import collections
import logging
import os
import os.path
import posixpath
from typing import Iterable, Iterator, Optional, Tuple

import glob2
import mkdocs.config
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav
import mkdocs.structure.pages

try:
    from mkdocs.exceptions import PluginError
except ImportError:
    PluginError = SystemExit

from mkdocs_literate_nav import parser

log = logging.getLogger(f"mkdocs.plugins.{__name__}")
log.addFilter(mkdocs.utils.warning_filter)


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (
        ("nav_file", mkdocs.config.config_options.Type(str, default="SUMMARY.md")),
        ("implicit_index", mkdocs.config.config_options.Type(bool, default=False)),
    )

    def on_files(self, files: mkdocs.structure.files.Files, config: mkdocs.config.Config):
        config["nav"] = resolve_directories_in_nav(
            config["nav"],
            files,
            nav_file_name=self.config["nav_file"],
            implicit_index=self.config["implicit_index"],
        )
        self._files = files

    def on_nav(
        self,
        nav: mkdocs.structure.nav.Navigation,
        config: mkdocs.config.Config,
        files: mkdocs.structure.files.Files,
    ):
        if files != self._files:
            log.warning(
                "The literate-nav plugin created the nav based on files that were subsequently modified by another MkDocs plugin! "
                "Re-order `plugins` in mkdocs.yml so that 'literate-nav' appears later."
            )


def resolve_directories_in_nav(
    nav_data, files: mkdocs.structure.files.Files, nav_file_name: str, implicit_index: bool
):
    """Walk through a standard MkDocs nav config and replace `directory/` references.

    Directories, if found, are resolved by the rules of literate nav insertion:
    If it has a literate nav file, that is used. Otherwise an implicit nav is generated.
    """

    def get_nav_for_dir(path: str) -> Optional[Tuple[str, str]]:
        file = files.get_file_from_path(os.path.join(path, nav_file_name))
        if not file:
            return None
        log.debug(f"Navigation for {path!r} based on {file.src_path!r}.")

        # https://github.com/mkdocs/mkdocs/blob/ff0b726056/mkdocs/structure/nav.py#L113
        # Prevent the warning in case the user doesn't also end up including this page in
        # the final nav, maybe they want it only for the purpose of feeding to this plugin.
        mkdocs.structure.pages.Page(None, file, {})

        # https://github.com/mkdocs/mkdocs/blob/fa5aa4a26e/mkdocs/structure/pages.py#L120
        with open(file.abs_src_path, encoding="utf-8-sig") as f:
            return nav_file_name, f.read()

    globber = MkDocsGlobber(files)
    nav_parser = parser.NavParser(get_nav_for_dir, globber, implicit_index=implicit_index)

    result = None
    if not nav_data or get_nav_for_dir("."):
        result = nav_parser.markdown_to_nav()
    if not result:
        result = nav_parser.resolve_yaml_nav(nav_data)
    return result or []


class MkDocsGlobber(glob2.Globber):
    def __init__(self, files: mkdocs.structure.files.Files):
        self.files = set()
        self.dirs = collections.defaultdict(dict)
        self.index_dirs = {}
        for f in files:
            if not f.is_documentation_page():
                continue
            path = f.src_path.replace(os.sep, "/")
            self.files.add(path)
            tail, head = posixpath.split(path)
            if f.name == "index":
                self.index_dirs[tail] = path
            while True:
                self.dirs[tail or "."][head] = True
                if not tail:
                    break
                tail, head = posixpath.split(tail)

    def listdir(self, path: str) -> Iterable[str]:
        if path not in self.dirs:
            raise NotADirectoryError(path)
        return self.dirs[path]

    def exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs

    def isdir(self, path: str) -> bool:
        return path in self.dirs

    def islink(self, path: str) -> bool:
        return False

    def iglob(self, *args, **kwargs) -> Iterator[str]:
        for p in super().iglob(*args, **kwargs):
            yield p.replace(os.sep, "/")

    def find_index(self, root: str) -> Optional[str]:
        if root in self.index_dirs:
            return self.index_dirs[root]
