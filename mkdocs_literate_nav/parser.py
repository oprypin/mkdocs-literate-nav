import copy
import functools
import itertools
import logging
import posixpath
import xml.etree.ElementTree as etree
from typing import Any, Callable, Dict, Iterator, List, Optional, Set, Tuple, Union

import markdown
import markdown.extensions
import markdown.preprocessors
import markdown.treeprocessors
import mkdocs.utils

from mkdocs_literate_nav import exceptions

log = logging.getLogger(f"mkdocs.plugins.{__name__}")
log.addFilter(mkdocs.utils.warning_filter)


NavItem = Dict[Optional[str], Union[str, Any]]
Nav = List[NavItem]
RootStack = Tuple[str, ...]


def markdown_to_nav(
    get_md_for_root: Callable[[str], Optional[str]],
    globber,
    roots: RootStack = ("",),
    seen_items: Optional[Set[str]] = None,
    *,
    implicit_index: bool = False,
) -> Nav:
    if seen_items is None:
        seen_items = set()
    if roots.count(roots[0]) > 1:
        rec = " -> ".join(repr(r) for r in reversed(roots))
        raise RecursionError(f"Disallowing recursion {rec}")
    get_nav_for_roots = functools.partial(
        markdown_to_nav, get_md_for_root, globber, implicit_index=implicit_index
    )
    root = roots[0]
    ext = _MarkdownExtension()
    md = get_md_for_root(root)
    if md:
        markdown.markdown(md, extensions=[ext])
    first_item = None
    if ext.nav and implicit_index:
        first_item = globber.find_index(root)
        if first_item:
            first_item = _Wildcard(first_item)
    if not ext.nav:
        log.debug(f"Navigation for {root!r} will be inferred.")
        markdown.markdown("* *", extensions=[ext])
    return make_nav(ext.nav, get_nav_for_roots, globber, roots, seen_items, first_item)


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


def make_nav(
    section: etree.Element,
    get_nav_for_roots: Callable[[RootStack], Nav],
    globber,
    roots: RootStack = ("",),
    seen_items: Optional[Set[str]] = None,
    first_item: Optional[str] = None,
) -> Nav:
    if seen_items is None:
        seen_items = set()
    assert section.tag in _LIST_TAGS
    result = []
    if first_item is not None:
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
                abs_link = out_item = posixpath.normpath(posixpath.join(roots[0], link).lstrip("/"))
                if abs_link == ".":
                    abs_link = ""
                if globber.isdir(abs_link):
                    try:
                        out_item = get_nav_for_roots((abs_link, *roots))
                    except RecursionError as e:
                        log.warning(f"{e} ({link!r})")
                out_title = "".join(child.itertext())
                child = next(children)
            if child.tag in _LIST_TAGS:
                out_item = make_nav(child, get_nav_for_roots, globber, roots, seen_items, out_item)
                child = next(children)
        except StopIteration:
            error = ""
        else:
            error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
        if out_title is None:
            error += "Did not find any title specified." + _EXAMPLES
        elif out_item is None:
            if "*" in out_title:
                out_item = _Wildcard(
                    posixpath.normpath(posixpath.join(roots[0], out_title).lstrip("/"))
                )
                out_title = None
            else:
                error += "Did not find any item/section content specified." + _EXAMPLES
        if error:
            raise LiterateNavParseError(error, item)

        if isinstance(out_item, str):
            seen_items.add(out_item)
        result.append({out_title: out_item})

    # Resolve globs.
    resolved = []
    for i, entry in enumerate(result):
        [(_, top_item)] = entry.items()
        if not isinstance(top_item, _Wildcard):
            resolved.append(entry)
            continue
        for item in globber.glob(top_item):
            if item in seen_items:
                continue
            seen_items.add(item)
            if globber.isdir(item):
                title = mkdocs.utils.dirname_to_title(posixpath.basename(item))
                try:
                    resolved.append({title: get_nav_for_roots((item, *roots))})
                except RecursionError as e:
                    log.warning(f"{e} ({item!r})")
                    resolved.append({title: item})
            else:
                resolved.append({None: item})
    return resolved


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
