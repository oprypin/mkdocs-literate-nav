import logging
import os.path
import pathlib
from typing import Iterable, Optional, Type

import mkdocs.config
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav
import mkdocs.structure.pages

from mkdocs_literate_nav import parser

log = logging.getLogger(f"mkdocs.plugins.{__name__}")
log.addFilter(mkdocs.utils.warning_filter)


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (("nav_file", mkdocs.config.config_options.Type(str)),)

    def on_nav(
        self,
        nav: mkdocs.structure.nav.Navigation,
        config: mkdocs.config.Config,
        files: mkdocs.structure.files.Files,
    ) -> mkdocs.structure.nav.Navigation:
        del nav

        # Reset the state from the internal `get_navigation` execution before running it again here.
        for file in files:
            file.page = None

        def read_index_of_dir(path: str) -> Optional[str]:
            file = _find_index_of_dir(self.config, files, path)
            if file:
                log.debug(f"Navigation for {path!r} based on {file.src_path!r}.")

                # https://github.com/mkdocs/mkdocs/blob/ff0b726056/mkdocs/structure/nav.py#L113
                # Prevent the warning in case the user doesn't also end up including this page in
                # the final nav, maybe they want it only for the purpose of feeding to this plugin.
                mkdocs.structure.pages.Page(None, file, self.config)

                # https://github.com/mkdocs/mkdocs/blob/fa5aa4a26e/mkdocs/structure/pages.py#L120
                with open(file.abs_src_path, encoding="utf-8-sig") as f:
                    return f.read()
            # Not found, return None.

        config["nav"] = parser.markdown_to_nav(read_index_of_dir)
        resolve_wildcards(config["nav"], files)

        return mkdocs.structure.nav.get_navigation(files, config)


def _find_index_of_dir(
    config: mkdocs.config.Config, files: mkdocs.structure.files.Files, path: str
) -> mkdocs.structure.files.File:
    """Find the directory's index (or nav if specified) Markdown file.

    If `nav_file` is configured, unconditionally get that file from this dir (could be None).
    Else try README.md. Else try whatever maps to the index (effectively index.md or readme.md).
    """
    if config.get("nav_file"):
        return files.get_file_from_path(os.path.join(path, config.get("nav_file")))
    f = files.get_file_from_path(os.path.join(path, "README.md"))
    if f:
        return f
    for f in files.documentation_pages():
        if os.path.split(f.src_path)[0] == path and f.name == "index":
            return f


def _walk_nav(nav: list, cls: Type) -> Iterable[list]:
    if isinstance(nav, cls):
        yield nav
    for item in nav:
        if isinstance(item, dict):
            (item,) = item.values()
            if isinstance(item, list):
                yield from _walk_nav(item, cls)
            elif isinstance(item, cls):
                yield item


def resolve_wildcards(nav: parser.NavWithWildcards, files: mkdocs.structure.files.Files) -> None:
    files = [f.src_path for f in files.documentation_pages()]
    explicit_files = set(_walk_nav(nav, str))

    for lst in _walk_nav(nav, list):
        for i in reversed(range(len(lst))):
            item = lst[i]
            if isinstance(item, parser.Wildcard):
                found = [f for f in files if pathlib.PurePath("/", f).match("/" + item)]
                if not found:
                    log.warning(f"No Markdown files found for {item!r}.")
                lst[i : i + 1] = (f for f in found if f not in explicit_files)
