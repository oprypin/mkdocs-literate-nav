import copy
import functools
import itertools
import logging
import posixpath
import xml.etree.ElementTree as etree
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple, Union

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


NavItem = Union[str, Dict[Optional[str], Union[str, Any]]]
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
        self.seen_items = set()
        self._warn = functools.lru_cache()(log.warning)

    def markdown_to_nav(self, roots: Tuple[str, ...] = (".",)) -> Nav:
        root = roots[0]
        ext = _MarkdownExtension()
        dir_nav = self.get_nav_for_dir(root)
        if dir_nav:
            nav_file_name, md = dir_nav
            markdown.markdown(md, extensions=[ext])
            if ext.nav:
                self.seen_items.add(posixpath.normpath(posixpath.join(root, nav_file_name)))
        first_item = None
        if ext.nav and self.implicit_index and root != ".":
            first_item = self.globber.find_index(root)
            if first_item:
                first_item = Wildcard(root, "/" + first_item, fallback=False)
        if not ext.nav:
            log.debug(f"Navigation for {root!r} will be inferred.")
            return self._resolve_wildcards([Wildcard(root, "*", fallback=False)], roots)
        return self._resolve_wildcards(self._list_element_to_nav(ext.nav, root, first_item), roots)

    def _list_element_to_nav(
        self, section: etree.Element, root: str, first_item: Optional[str] = None
    ):
        assert section.tag in _LIST_TAGS
        result = []
        if first_item is not None:
            if isinstance(first_item, str):
                self.seen_items.add(first_item)
            result.append(first_item)
        for item in section:
            assert item.tag == "li"
            out_title = item.text
            out_item = None

            children = _iter_children_without_tail(item)
            try:
                child = next(children)
                if not out_title and child.tag == "a":
                    link = child.get("href")
                    out_item = self._maybe_directory_wildcard(root, link)
                    out_title = _unescape("".join(child.itertext()))
                    child = next(children)
                if child.tag in _LIST_TAGS:
                    out_item = self._list_element_to_nav(child, root, out_item)
                    child = next(children)
            except StopIteration:
                error = ""
            else:
                error = f"Expected no more elements, but got {_to_short_string(child)}.\n"
            if out_title is None:
                error += "Did not find any title specified." + _EXAMPLES
            elif out_item is None:
                if "*" in out_title:
                    out_item = Wildcard(root, out_title)
                    out_title = None
                else:
                    error += "Did not find any item/section content specified." + _EXAMPLES
            if error:
                raise LiterateNavParseError(error, item)

            if type(out_item) in (str, list, DirectoryWildcard) and out_title is not None:
                out_item = {out_title: out_item}
            result.append(out_item)
        return result

    def _maybe_directory_wildcard(self, root: str, link: str) -> Union["Wildcard", str]:
        abs_link = posixpath.normpath(posixpath.join(root, link))
        self.seen_items.add(abs_link)
        if link.endswith("/") and self.globber.isdir(abs_link):
            return DirectoryWildcard(root, link)
        return abs_link

    def _resolve_wildcards(self, nav, roots: RootStack = (".",)) -> Nav:
        def can_recurse(new_root):
            if new_root in roots:
                rec = " -> ".join(repr(r) for r in reversed((new_root,) + roots))
                self._warn(f"Disallowing recursion {rec}")
                return False
            return True

        # Ensure depth-first processing, so separate loop for recursive calls first.
        for entry in nav:
            if isinstance(entry, dict) and len(entry) == 1:
                [(key, val)] = entry.items()
                if isinstance(entry, str):
                    entry = val
            if isinstance(entry, str):
                self.seen_items.add(entry)

        resolved: Nav = []
        for entry in nav:
            if isinstance(entry, dict) and len(entry) == 1:
                [(key, val)] = entry.items()
                if isinstance(val, list):
                    entry[key] = self._resolve_wildcards(val, roots)
                elif isinstance(val, DirectoryWildcard):
                    entry[key] = (
                        self.markdown_to_nav((val.value,) + roots)
                        if can_recurse(val.value)
                        else val.fallback
                    )
                elif isinstance(val, Wildcard):
                    entry[key] = self._resolve_wildcards([val], roots) or val.fallback
                if entry[key]:
                    resolved.append(entry)
                continue

            assert not isinstance(entry, DirectoryWildcard)
            if not isinstance(entry, Wildcard):
                resolved.append(entry)
                continue

            any_matches = False
            for item in self.globber.glob(entry.value.rstrip("/")):
                any_matches = True
                if item in self.seen_items:
                    continue
                if self.globber.isdir(item):
                    title = mkdocs.utils.dirname_to_title(posixpath.basename(item))
                    subitems = self.markdown_to_nav((item,) + roots)
                    if subitems:
                        resolved.append({title: subitems})
                else:
                    if entry.value.endswith("/"):
                        continue
                    resolved.append({None: item})
                self.seen_items.add(item)
            if not any_matches and entry.fallback:
                resolved.append(entry.fallback)
        return resolved

    def resolve_yaml_nav(self, nav: Nav) -> Nav:
        if not isinstance(nav, list):
            return nav
        return self._resolve_wildcards([self._resolve_yaml_nav(x) for x in nav])

    def _resolve_yaml_nav(self, item: NavItem):
        if isinstance(item, str) and "*" in item:
            return Wildcard("", item)
        if isinstance(item, dict) and len(item) == 1:
            [(key, val)] = item.items()
            if isinstance(val, list):
                val = [self._resolve_yaml_nav(x) for x in val]
            elif isinstance(val, str) and "*" in val:
                val = Wildcard("", val)
            elif isinstance(val, str):
                val = self._maybe_directory_wildcard("", val)
            return {key: val}
        return item


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


class Wildcard:
    trim_slash = False

    def __init__(self, *path_parts: str, fallback: bool = True):
        norm = posixpath.normpath(posixpath.join(*path_parts).lstrip("/"))
        if path_parts[-1].endswith("/") and not self.trim_slash:
            norm += "/"
        self.value = norm
        self.fallback = path_parts[-1] if fallback else None

    def __str__(self):
        return f"{type(self).__name__}({self.value!r})"


class DirectoryWildcard(Wildcard):
    trim_slash = True


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
