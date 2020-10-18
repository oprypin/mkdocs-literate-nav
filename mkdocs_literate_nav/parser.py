import copy
import io
import os
import xml.etree.ElementTree as etree
from typing import Iterator

import markdown
import markdown.extensions
import markdown.preprocessors
import markdown.treeprocessors


def markdown_to_nav(input_file: os.PathLike) -> dict:
    ext = _MarkdownExtension()
    markdown.markdownFromFile(
        input=input_file, output=io.BytesIO(), extensions=[ext],
    )
    return ext.nav


_NAME = "mkdocs_literate_nav"


class _MarkdownExtension(markdown.extensions.Extension):
    @property
    def nav(self):
        return self._treeprocessor.nav

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
        self.nav = []
        for top_level_item in doc:
            if top_level_item.text == nav_placeholder:
                self.nav = None
            elif top_level_item.tag in _LIST_TAGS and self.nav is None:
                self.nav = make_nav(top_level_item)


_LIST_TAGS = ("ul", "ol")
_EXAMPLES = """
Examples:
    * [Item title](item_content.md)
    * Section title
        * [Sub content](sub/content.md)
"""


def make_nav(section: etree.Element, *, first_item=None) -> list:
    assert section.tag in _LIST_TAGS
    result = []
    if first_item is not None:
        result.append(first_item)
    for item in section:
        result.append(_process_list_item(item))
    return result


def _process_list_item(item: etree.Element) -> dict:
    assert item.tag == "li"
    out_title = item.text
    out_item = None

    children = _iter_children_without_tail(item)
    try:
        child = next(children)
        if not out_title and child.tag == "a":
            out_item = child.get("href")
            out_title = "".join(child.itertext())
            child = next(children)
        if child.tag in _LIST_TAGS:
            out_item = make_nav(child, first_item=out_item)
            child = next(children)
    except StopIteration:
        error = ""
    else:
        error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
    if out_title is None:
        error += "Did not find any title specified." + _EXAMPLES
    elif out_item is None:
        error += "Did not find any item/section content specified." + _EXAMPLES
    if error:
        raise LiterateNavParseError(error, item)

    return {out_title: out_item}


def _iter_children_without_tail(element: etree.Element) -> Iterator[etree.Element]:
    for child in element:
        yield child
        if child.tail:
            raise LiterateNavParseError(
                f"Expected no text after {_to_short_string(child)}, but got {child.tail!r}", element
            )


def _to_short_string(el: etree.Element) -> str:
    el = copy.deepcopy(el)
    for child in el:
        if child:
            del child[:]
            child.text = "[...]"
    return etree.tostring(el, encoding="unicode")
