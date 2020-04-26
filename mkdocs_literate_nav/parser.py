import io

import markdown.extensions
import markdown.treeprocessors


def markdown_to_nav(input_file):
    ext = _MarkdownExtension()
    markdown.markdownFromFile(
        input=input_file, output=io.BytesIO(), extensions=[ext],
    )
    return ext.nav


class _MarkdownExtension(markdown.extensions.Extension):
    @property
    def nav(self):
        return self._treeprocessor.nav

    def extendMarkdown(self, md):
        self._treeprocessor = _Treeprocessor(md)
        md.treeprocessors.register(self._treeprocessor, "mkdocs_literate_nav", 0)


class _Treeprocessor(markdown.treeprocessors.Treeprocessor):
    LIST_TAGS = ("ul", "ol")

    def _make_nav(self, section):
        for item in section:
            assert item.tag == "li"
            sub = list(_etree_children(item))
            if len(sub) == 3 and not sub[0] and sub[1].tag == "a" and not sub[2]:
                link = sub[1]
                sub = list(_etree_children(link))
                if len(sub) == 1:
                    yield (sub[0], link.get("href"))
                    continue
            if len(sub) == 3 and sub[0] and sub[1].tag in self.LIST_TAGS and not sub[2]:
                yield (sub[0], list(self._make_nav(sub[1])))
                continue

    def run(self, doc):
        self.nav = []
        for top_level_item in doc:
            if top_level_item.tag in self.LIST_TAGS:
                self.nav = list(self._make_nav(top_level_item))
        return doc


def _etree_children(el):
    text = el.text or ""
    yield text.strip() and text
    for child in el:
        yield child
        text = child.tail or ""
        yield text.strip() and text
