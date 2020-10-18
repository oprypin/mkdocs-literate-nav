import io
import os

import markdown
import markdown.extensions
import markdown.preprocessors
import markdown.treeprocessors

from mkdocs_literate_nav import util


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


class _Treeprocessor(markdown.treeprocessors.Treeprocessor):
    LIST_TAGS = ("ul", "ol")

    @util.collect
    def _make_nav(self, section):
        for item in section:
            assert item.tag == "li"
            sub = _etree_children(item)
            if len(sub) == 3 and not sub[0] and sub[1].tag == "a" and not sub[2]:
                link = sub[1]
                sub = _etree_children(link)
                if len(sub) == 1:
                    yield {sub[0]: link.get("href")}
                    continue
            if len(sub) == 3 and sub[0] and sub[1].tag in self.LIST_TAGS and not sub[2]:
                yield {sub[0]: self._make_nav(sub[1])}
                continue

    def run(self, doc):
        nav_placeholder = getattr(self.md.preprocessors[_NAME], "nav_placeholder", object())
        self.nav = []
        for top_level_item in doc:
            if top_level_item.text == nav_placeholder:
                self.nav = None
            elif top_level_item.tag in self.LIST_TAGS and self.nav is None:
                self.nav = self._make_nav(top_level_item)


@util.collect
def _etree_children(el):
    text = el.text or ""
    yield text.strip() and text
    for child in el:
        yield child
        text = child.tail or ""
        yield text.strip() and text
