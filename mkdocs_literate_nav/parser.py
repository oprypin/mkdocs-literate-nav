import copy
import functools
import posixpath
import xml.etree.ElementTree as etree
from typing import Any, Callable, Dict, Iterator, List, Optional, Union

import markdown
import markdown.extensions
import markdown.preprocessors
import markdown.treeprocessors

NavItem = Dict[Union[None, str, type(Ellipsis)], Union[str, Any]]
Nav = List[NavItem]


def markdown_to_nav(
    get_md_for_root: Callable[[str], Optional[str]], root: str = ""
) -> Optional[Nav]:
    ext = _MarkdownExtension()
    md = get_md_for_root(root)
    if md:
        markdown.markdown(md, extensions=[ext])
        if ext.nav:
            return make_nav(ext.nav, functools.partial(markdown_to_nav, get_md_for_root), root)


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
                yield self.nav_placeholder + "\n"
            else:
                yield line


class LiterateNavParseError(Exception):
    def __init__(self, message, el):
        super().__init__(message + "\nThe problematic item:\n\n" + _to_short_string(el))


class _Treeprocessor(markdown.treeprocessors.Treeprocessor):
    def run(self, doc):
        nav_placeholder = getattr(self.md.preprocessors[_NAME], "nav_placeholder", object())
        nav_index = next((i for i, el in enumerate(doc) if el.text == nav_placeholder), -1)
        for i, el in enumerate(doc):
            if el.tag in _LIST_TAGS and i > nav_index:
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
    get_nav_for_root: Callable[[str], Optional[Nav]],
    root: str = "",
    *,
    first_item: Optional[str] = None,
) -> Nav:
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
                out_item = posixpath.join(root, child.get("href"))
                if out_item.endswith("/"):
                    out_item = get_nav_for_root(out_item[:-1]) or out_item
                out_title = "".join(child.itertext())
                child = next(children)
            if child.tag in _LIST_TAGS:
                out_item = make_nav(child, get_nav_for_root, root, first_item=out_item)
                child = next(children)
        except StopIteration:
            error = ""
        else:
            error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
        if out_title is None:
            error += "Did not find any title specified." + _EXAMPLES
        elif out_item is None:
            if out_title == "...":
                out_title = ...
                out_item = root
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
