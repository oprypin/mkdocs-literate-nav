import copy
import functools
import itertools
import logging
import posixpath
import xml.etree.ElementTree as etree
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

import markdown
import markdown.extensions
import markdown.preprocessors
import markdown.treeprocessors
import mkdocs.utils

from mkdocs_literate_nav import exceptions

log = logging.getLogger(f"mkdocs.plugins.{__name__}")
log.addFilter(mkdocs.utils.warning_filter)


class Wildcard(str):
    pass


NavItem = Dict[Optional[str], Union[str, Any]]
Nav = List[NavItem]
NavWithWildcards = List[Union[NavItem, Wildcard]]
RootStack = Tuple[str, ...]


def markdown_to_nav(
    get_md_for_root: Callable[[str], Optional[str]], roots: RootStack = ("",)
) -> Optional[NavWithWildcards]:
    root = roots[0]
    ext = _MarkdownExtension()
    md = get_md_for_root(root)
    if md:
        markdown.markdown(md, extensions=[ext])
        if ext.nav:
            return make_nav(ext.nav, functools.partial(markdown_to_nav, get_md_for_root), roots)
    log.debug(f"Navigation for {root!r} will be inferred.")
    return [Wildcard(_path_join(root, "*"))]


_NAME = "mkdocs_literate_nav"


class _MarkdownExtension(markdown.extensions.Extension):
    @property
    def nav(self) -> etree.Element:
        return getattr(self._treeprocessor, "nav", None)

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
        * ...
"""


def make_nav(
    section: etree.Element,
    get_nav_for_roots: Callable[[RootStack], Optional[NavWithWildcards]],
    roots: RootStack = ("",),
    first_item: Optional[str] = None,
) -> NavWithWildcards:
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
                abs_link = _path_join(roots[0], link)
                out_item = abs_link or "."
                if link.endswith("/"):
                    if abs_link in roots:
                        log.warning(f"Disallowing recursion from {roots[0]!r} into {link!r}")
                    else:
                        sub_nav = get_nav_for_roots((abs_link, *roots))
                        if sub_nav:
                            out_item = sub_nav
                out_title = "".join(child.itertext())
                child = next(children)
            if child.tag in _LIST_TAGS:
                out_item = make_nav(child, get_nav_for_roots, roots, first_item=out_item)
                child = next(children)
        except StopIteration:
            error = ""
        else:
            error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
        if out_title is None:
            error += "Did not find any title specified." + _EXAMPLES
        elif out_item is None:
            if "*" in out_title:
                result.append(Wildcard(_path_join(roots[0], out_title)))
                if not error:
                    continue
            else:
                error += "Did not find any item/section content specified." + _EXAMPLES
        if error:
            raise LiterateNavParseError(error, item)

        result.append({out_title: out_item})
    return result


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


def _path_join(*path: str) -> str:
    result = posixpath.normpath(posixpath.join(*path)).lstrip("/")
    return "" if result == "." else result
