from __future__ import annotations

import fnmatch
import logging
import os
import os.path
import re
from pathlib import PurePath, PurePosixPath
from typing import Iterator

import mkdocs.config
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav
import mkdocs.structure.pages

try:
    from mkdocs.plugins import event_priority
except ImportError:
    event_priority = lambda priority: lambda f: f  # No-op fallback


from mkdocs_literate_nav import parser

log = logging.getLogger(f"mkdocs.plugins.{__name__}")


class _PluginConfig:
    nav_file = mkdocs.config.config_options.Type(str, default="SUMMARY.md")
    implicit_index = mkdocs.config.config_options.Type(bool, default=False)
    markdown_extensions = mkdocs.config.config_options.MarkdownExtensions()
    tab_length = mkdocs.config.config_options.Type(int, default=4)


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = tuple(
        (k, v)
        for k, v in _PluginConfig.__dict__.items()
        if isinstance(v, mkdocs.config.config_options.BaseConfigOption)
    )

    @event_priority(-100)  # Run last
    def on_files(self, files: mkdocs.structure.files.Files, config: mkdocs.config.Config) -> None:
        config["nav"] = resolve_directories_in_nav(
            config["nav"],
            files,
            nav_file_name=self.config["nav_file"],
            implicit_index=self.config["implicit_index"],
            markdown_config=dict(
                extensions=self.config["markdown_extensions"],
                extension_configs=self.config["mdx_configs"],
                tab_length=self.config["tab_length"],
            ),
        )
        self._files = files

    def on_nav(
        self,
        nav: mkdocs.structure.nav.Navigation,
        config: mkdocs.config.Config,
        files: mkdocs.structure.files.Files,
    ) -> None:
        if files != getattr(self, "_files", None):
            log.warning(
                "The literate-nav plugin created the nav based on files that were subsequently modified by another MkDocs plugin! "
                "Re-order `plugins` in mkdocs.yml so that 'literate-nav' appears later."
            )


def resolve_directories_in_nav(
    nav_data,
    files: mkdocs.structure.files.Files,
    nav_file_name: str,
    implicit_index: bool,
    markdown_config: dict | None = None,
):
    """Walk through a standard MkDocs nav config and replace `directory/` references.

    Directories, if found, are resolved by the rules of literate nav insertion:
    If it has a literate nav file, that is used. Otherwise an implicit nav is generated.
    """

    def get_nav_for_dir(path: str) -> tuple[str, str] | None:
        file = files.get_file_from_path(os.path.join(path, nav_file_name))
        if not file:
            return None
        log.debug(f"Navigation for {path!r} based on {file.src_path!r}.")

        # Prevent the warning in case the user doesn't also end up including this page in
        # the final nav, maybe they want it only for the purpose of feeding to this plugin.
        try:  # MkDocs 1.5+
            if file.inclusion.is_in_nav():
                file.inclusion = mkdocs.structure.files.InclusionLevel.NOT_IN_NAV
        except AttributeError:
            # https://github.com/mkdocs/mkdocs/blob/ff0b726056/mkdocs/structure/nav.py#L113
            mkdocs.structure.pages.Page(None, file, {})  # type: ignore

        # https://github.com/mkdocs/mkdocs/blob/fa5aa4a26e/mkdocs/structure/pages.py#L120
        with open(file.abs_src_path, encoding="utf-8-sig") as f:
            return nav_file_name, f.read()

    globber = MkDocsGlobber(files)
    nav_parser = parser.NavParser(
        get_nav_for_dir, globber, implicit_index=implicit_index, markdown_config=markdown_config
    )

    result = None
    if not nav_data or get_nav_for_dir("."):
        result = nav_parser.markdown_to_nav()
    if not result:
        result = nav_parser.resolve_yaml_nav(nav_data)
    return result or []


class MkDocsGlobber:
    def __init__(self, files: mkdocs.structure.files.Files):
        self.files = {}  # Ordered set
        self.dirs = {}  # Ordered set
        self.index_dirs = {}
        for f in files:
            if not f.is_documentation_page():
                continue
            path = PurePosixPath("/", PurePath(f.src_path).as_posix())
            self.files[path] = True
            tail, head = path.parent, path.name
            if f.name == "index":
                self.index_dirs[tail] = path
            while True:
                self.dirs[tail] = True
                if not head:
                    break
                tail, head = tail.parent, tail.name

    def isdir(self, path: str) -> bool:
        return PurePosixPath("/", path) in self.dirs

    def glob(self, pattern: str) -> Iterator[str]:
        pat_parts = PurePosixPath("/" + pattern).parts
        re_parts = [re.compile(fnmatch.translate(part)) for part in pat_parts]

        for collection in self.files, self.dirs:
            for path in collection:
                if len(path.parts) == len(re_parts):
                    zipped = zip(path.parts, re_parts)
                    next(zipped)  # Both the path and the pattern have a slash as their first part.
                    if all(re_part.match(part) for part, re_part in zipped):
                        yield str(path)[1:]

    def find_index(self, root: str) -> str | None:
        root_path = PurePosixPath("/", root)
        if root_path in self.index_dirs:
            return str(self.index_dirs[root_path])[1:]
        return None
