from __future__ import annotations

import copy
import functools
import itertools
import logging
import posixpath
import urllib.parse
import xml.etree.ElementTree as etree
from collections.abc import Iterator
from typing import TYPE_CHECKING, Callable, Optional, Union, cast

import markdown
import markdown.extensions
import markdown.postprocessors
import markdown.preprocessors
import markdown.treeprocessors
import mkdocs.utils

from mkdocs_literate_nav import exceptions

if TYPE_CHECKING:
    from .plugin import MkDocsGlobber


log = logging.getLogger(f"mkdocs.plugins.{__name__}")

_unescape: Callable[[str], str]
try:
    _unescape = markdown.treeprocessors.UnescapeTreeprocessor().unescape
except AttributeError:
    _unescape = markdown.postprocessors.UnescapePostprocessor().run  # type: ignore[attr-defined]


class Wildcard:
    trim_slash = False

    def __init__(self, *path_parts: str, fallback: bool = True):
        norm = posixpath.normpath(posixpath.join(*path_parts).lstrip("/"))
        if path_parts[-1].endswith("/") and not self.trim_slash:
            norm += "/"
        self.value = norm
        self.fallback = path_parts[-1] if fallback else None

    def __repr__(self):
        return f"{type(self).__name__}({self.value!r})"


if TYPE_CHECKING:
    NavWithWildcardsItem = Union[
        Wildcard,
        str,
        "NavWithWildcards",
        dict[Optional[str], Union[Wildcard, str, "NavWithWildcards"]],
    ]
    NavWithWildcards = list[NavWithWildcardsItem]

    NavItem = Union[str, dict[Optional[str], Union[str, "Nav"]]]
    Nav = list[NavItem]

    RootStack = tuple[str, ...]


class DirectoryWildcard(Wildcard):
    trim_slash = True


class NavParser:
    def __init__(
        self,
        get_nav_for_dir: Callable[[str], tuple[str, str] | None],
        globber: MkDocsGlobber,
        *,
        implicit_index: bool = False,
        markdown_config: dict | None = None,
    ):
        self.get_nav_for_dir = get_nav_for_dir
        self.globber = globber
        self.implicit_index = implicit_index
        self._markdown_config = markdown_config or {}
        self.seen_items: set[str] = set()
        self._warn = functools.lru_cache()(log.warning)

    def markdown_to_nav(self, roots: tuple[str, ...] = (".",)) -> Nav:
        root = roots[0]

        if dir_nav := self.get_nav_for_dir(root):
            nav_file_name, markdown_content = dir_nav
            nav = _extract_nav_from_content(self._markdown_config, markdown_content)

            if nav is not None:
                self_path = posixpath.normpath(posixpath.join(root, nav_file_name))
                if not (self.implicit_index and self_path == self.globber.find_index(root)):
                    self.seen_items.add(self_path)

                first_item: Wildcard | None = None
                if self.implicit_index:
                    if found_index := self.globber.find_index(root):
                        first_item = Wildcard(root, "/" + found_index, fallback=False)
                return self._resolve_wildcards(
                    self._list_element_to_nav(nav, root, first_item), roots
                )

        log.debug(f"Navigation for {root!r} will be inferred.")
        return self._resolve_wildcards([Wildcard(root, "*", fallback=False)], roots)

    def _list_element_to_nav(
        self, section: etree.Element, root: str, first_item: Wildcard | str | None = None
    ) -> NavWithWildcards:
        assert section.tag in _LIST_TAGS
        result: NavWithWildcards = []
        if first_item is not None:
            if isinstance(first_item, str):
                self.seen_items.add(first_item)
            result.append(first_item)
        for item in section:
            assert item.tag == "li"
            out_title = item.text
            out_item: Wildcard | str | list | None = None

            children = _iter_children_without_tail(item)
            try:
                child = next(children)
                if not out_title and child.tag == "a":
                    if link := child.get("href"):
                        out_item = self._resolve_string_item(root, link)
                        out_title = _unescape("".join(child.itertext()))
                    child = next(children)
                if child.tag in _LIST_TAGS:
                    out_item = self._list_element_to_nav(
                        child, root, cast("Union[Wildcard, str, None]", out_item)
                    )
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

            assert out_item is not None
            if type(out_item) in (str, list, DirectoryWildcard) and out_title is not None:
                result.append({out_title: out_item})
            else:
                result.append(out_item)
        return result

    def _resolve_string_item(self, root: str, link: str) -> Wildcard | str:
        parsed = urllib.parse.urlsplit(link)
        if parsed.scheme or parsed.netloc:
            return link

        abs_link = posixpath.normpath(posixpath.join(root, link))
        self.seen_items.add(abs_link)
        if link.endswith("/") and self.globber.isdir(abs_link):
            return DirectoryWildcard(root, link)
        return abs_link

    def _resolve_wildcards(self, nav: NavWithWildcards, roots: RootStack = (".",)) -> Nav:
        def can_recurse(new_root: str) -> bool:
            if new_root in roots:
                rec = " -> ".join(repr(r) for r in reversed((new_root, *roots)))
                self._warn(f"Disallowing recursion {rec}")
                return False
            return True

        # Ensure depth-first processing, so separate loop for recursive calls first.
        for entry in nav:
            if isinstance(entry, dict) and len(entry) == 1:
                [(key, val)] = entry.items()
                if isinstance(val, str):
                    entry = val
            if isinstance(entry, str):
                self.seen_items.add(entry)

        resolved: Nav = []
        for entry in nav:
            if isinstance(entry, dict) and len(entry) == 1:
                [(key, val)] = entry.items()
                new_val: str | Nav | None = None
                if isinstance(val, list):
                    new_val = self._resolve_wildcards(val, roots)
                elif isinstance(val, DirectoryWildcard):
                    new_val = (
                        self.markdown_to_nav((val.value, *roots))
                        if can_recurse(val.value)
                        else val.fallback
                    )
                elif isinstance(val, Wildcard):
                    new_val = self._resolve_wildcards([val], roots) or val.fallback
                else:
                    new_val = val
                if new_val:
                    resolved.append({key: new_val})
                continue

            assert not isinstance(entry, (DirectoryWildcard, list, dict))
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
                    if subitems := self.markdown_to_nav((item, *roots)):
                        resolved.append({title: subitems})
                else:
                    if entry.value.endswith("/"):
                        continue
                    resolved.append({None: item})
                self.seen_items.add(item)
            if not any_matches and entry.fallback:
                resolved.append(entry.fallback)
        return resolved

    def resolve_yaml_nav(self, nav) -> Nav:
        if not isinstance(nav, list):
            return nav
        return self._resolve_wildcards([self._resolve_yaml_nav(x) for x in nav])

    def _resolve_yaml_nav(self, item) -> NavWithWildcardsItem:
        if isinstance(item, str) and "*" in item:
            return Wildcard("", item)
        if isinstance(item, dict):
            assert len(item) == 1
            [(key, val)] = item.items()
            if isinstance(val, list):
                return {key: [self._resolve_yaml_nav(x) for x in val]}
            if isinstance(val, str):
                if "*" in val:
                    return {key: Wildcard("", val)}
                return {key: self._resolve_string_item("", val)}
            return {key: val}
        return item


def _extract_nav_from_content(markdown_config: dict, markdown_content: str) -> etree.Element | None:
    md = markdown.Markdown(**markdown_config)
    md.inlinePatterns.deregister("html", strict=False)
    md.inlinePatterns.deregister("entity", strict=False)
    preprocessor = _Preprocessor(md)
    preprocessor._register()
    treeprocessor = _Treeprocessor(md)
    treeprocessor._register()
    md.convert(markdown_content)
    return treeprocessor.nav


class _Preprocessor(markdown.preprocessors.Preprocessor):
    nav_placeholder: str | None = None

    def run(self, lines: list[str]) -> list[str]:
        for i, line in enumerate(lines):
            if line.strip() == "<!--nav-->":
                self.nav_placeholder = self.md.htmlStash.store("")
                lines[i] = self.nav_placeholder + "\n"
        return lines

    def _register(self) -> None:
        self.md.preprocessors.register(self, "mkdocs_literate_nav", priority=25)


class _Treeprocessor(markdown.treeprocessors.Treeprocessor):
    nav: etree.Element | None = None

    def run(self, root: etree.Element) -> None:
        preprocessor: _Preprocessor = self.md.preprocessors["mkdocs_literate_nav"]  # type: ignore[assignment]
        nav_placeholder = preprocessor.nav_placeholder
        items: Iterator[etree.Element]
        if nav_placeholder is not None:
            # Will look for the first list after the last <!--nav-->.
            items = itertools.dropwhile(lambda el: el.text != nav_placeholder, root)
        else:
            # Will look for the last list.
            items = reversed(root)
        for el in items:
            if el.tag in _LIST_TAGS:
                self.nav = copy.deepcopy(el)
                break

    def _register(self) -> None:
        self.md.treeprocessors.register(self, "mkdocs_literate_nav", priority=19)


_LIST_TAGS = ("ul", "ol")
_EXAMPLES = """
Examples:
    * [Item title](item_content.md)
    * Section title
        * [Sub content](sub/content.md)
        * *.md
"""


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
        if len(child):
            del child[:]
            child.text = "[...]"
    el.tail = None
    return etree.tostring(el, encoding="unicode")


class LiterateNavParseError(exceptions.LiterateNavError):
    def __init__(self, message, el):
        super().__init__(message + "\nThe problematic item:\n\n" + _to_short_string(el))
