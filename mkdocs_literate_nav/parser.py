import copy
import itertools
import logging
import posixpath
import xml.etree.ElementTree as etree
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

import markdown
import markdown.extensions
import markdown.postprocessors
import markdown.preprocessors
import markdown.treeprocessors
import mkdocs.utils

from mkdocs_literate_nav import exceptions

log = logging.getLogger(f"mkdocs.plugins.{__name__}")
log.addFilter(mkdocs.utils.warning_filter)

_unescape = markdown.postprocessors.UnescapePostprocessor().run


NavItem = Dict[Optional[str], Union[str, Any]]
Nav = List[NavItem]
RootStack = Tuple[str, ...]


class NavParser:
    def __init__(
        self,
        get_nav_for_dir: Callable[[str], Optional[Tuple[str, str]]],
        globber,
        implicit_index: bool = False,
    ):
        self.get_nav_for_dir = get_nav_for_dir
        self.globber = globber
        self.implicit_index = implicit_index

    def markdown_to_nav(self, roots: RootStack = ("",)) -> Nav:
        seen_items = set()
        if roots.count(roots[0]) > 1:
            rec = " -> ".join(repr(r) for r in reversed(roots))
            raise RecursionError(f"Disallowing recursion {rec}")
        root = roots[0]
        ext = _MarkdownExtension()
        dir_nav = self.get_nav_for_dir(root)
        if dir_nav:
            nav_file_name, md = dir_nav
            markdown.markdown(md, extensions=[ext])
            if ext.nav:
                seen_items.add(posixpath.normpath(posixpath.join(root, nav_file_name)))
        first_item = None
        if ext.nav and self.implicit_index:
            first_item = self.globber.find_index(root)
            if first_item:
                first_item = _Wildcard(first_item)
        if not ext.nav:
            log.debug(f"Navigation for {root!r} will be inferred.")
            markdown.markdown("* *", extensions=[ext])
        return self._make_nav(ext.nav, roots, seen_items, first_item)

    def _make_nav(
        self,
        section: etree.Element,
        roots: RootStack,
        seen_items: Set[str],
        first_item: Optional[str] = None,
    ) -> Nav:
        assert section.tag in _LIST_TAGS
        result = []
        if first_item is not None:
            if type(first_item) is str:
                seen_items.add(first_item)
            result.append({None: first_item})
        for item in section:
            assert item.tag == "li"
            out_title = item.text
            out_item = None

            children = _iter_children_without_tail(item)
            try:
                child = next(children)
                if not out_title and child.tag == "a":
                    link = child.get("href")
                    abs_link = out_item = posixpath.normpath(
                        posixpath.join(roots[0], link).lstrip("/")
                    )
                    if abs_link == ".":
                        abs_link = ""
                    if link.endswith("/") and self.globber.isdir(abs_link):
                        try:
                            out_item = self.markdown_to_nav((abs_link, *roots))
                        except RecursionError as e:
                            log.warning(f"{e} ({link!r})")
                    out_title = _unescape("".join(child.itertext()))
                    child = next(children)
                if child.tag in _LIST_TAGS:
                    out_item = self._make_nav(child, roots, seen_items, out_item)
                    child = next(children)
            except StopIteration:
                error = ""
            else:
                error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
            if out_title is None:
                error += "Did not find any title specified." + _EXAMPLES
            elif out_item is None:
                if "*" in out_title:
                    norm = posixpath.normpath(posixpath.join(roots[0], out_title).lstrip("/"))
                    if out_title.endswith("/"):
                        norm += "/"
                    out_item = _Wildcard(norm)
                    out_title = None
                else:
                    error += "Did not find any item/section content specified." + _EXAMPLES
            if error:
                raise LiterateNavParseError(error, item)

            if type(out_item) is str:
                seen_items.add(out_item)
            result.append({out_title: out_item})

        # Resolve globs.
        resolved = []
        for i, entry in enumerate(result):
            [(_, top_item)] = entry.items()
            if not isinstance(top_item, _Wildcard):
                resolved.append(entry)
                continue
            for item in self.globber.glob(top_item.rstrip("/")):
                if item in seen_items:
                    continue
                if self.globber.isdir(item):
                    title = mkdocs.utils.dirname_to_title(posixpath.basename(item))
                    try:
                        resolved.append({title: self.markdown_to_nav((item, *roots))})
                    except RecursionError as e:
                        log.warning(f"{e} ({item!r})")
                        resolved.append({title: item})
                else:
                    if top_item.endswith("/"):
                        continue
                    resolved.append({None: item})
                seen_items.add(item)
        return resolved


_NAME = "mkdocs_literate_nav"


class _MarkdownExtension(markdown.extensions.Extension):
    _treeprocessor: "_Treeprocessor"

    @property
    def nav(self) -> Optional[etree.Element]:
        try:
            return self._treeprocessor.nav
        except AttributeError:
            return None

    def extendMarkdown(self, md):
        md.inlinePatterns.deregister("html", strict=False)
        md.inlinePatterns.deregister("entity", strict=False)
        md.preprocessors.register(_Preprocessor(md), _NAME, 25)
        self._treeprocessor = _Treeprocessor(md)
        md.treeprocessors.register(self._treeprocessor, _NAME, 19)


class _Preprocessor(markdown.preprocessors.Preprocessor):
    def run(self, lines):
        for line in lines:
            if line.strip() == "<!--nav-->":
                self.nav_placeholder = self.md.htmlStash.store("")
                line = self.nav_placeholder + "\n"
            yield line


class _Treeprocessor(markdown.treeprocessors.Treeprocessor):
    nav: etree.Element

    def run(self, doc):
        try:
            nav_placeholder = self.md.preprocessors[_NAME].nav_placeholder
        except AttributeError:
            # Will look for the last list.
            items = reversed(doc)
        else:
            # Will look for the first list after the last <!--nav-->.
            items = itertools.dropwhile(lambda el: el.text != nav_placeholder, doc)
        for el in items:
            if el.tag in _LIST_TAGS:
                self.nav = copy.deepcopy(el)
                break


_LIST_TAGS = ("ul", "ol")
_EXAMPLES = """
Examples:
    * [Item title](item_content.md)
    * Section title
        * [Sub content](sub/content.md)
        * *.md
"""


class _Wildcard(str):
    def __repr__(self):
        return f"Wildcard({super().__repr__()})"


def _iter_children_without_tail(element: etree.Element) -> Iterator[etree.Element]:
    for child in element:
        yield child
        if child.tail:
            raise LiterateNavParseError(
                f"Expected no text after {_to_short_string(child)}, but got {child.tail!r}.",
                element,
            )


def _to_short_string(el: etree.Element) -> str:
    el = copy.deepcopy(el)
    for child in el:
        if child:
            del child[:]
            child.text = "[...]"
    el.tail = None
    return etree.tostring(el, encoding="unicode")


class LiterateNavParseError(exceptions.LiterateNavError):
    def __init__(self, message, el):
        super().__init__(message + "\nThe problematic item:\n\n" + _to_short_string(el))
