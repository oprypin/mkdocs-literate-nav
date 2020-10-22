import os.path
import pathlib
from typing import Optional

import mkdocs.config
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav
import mkdocs.structure.pages

from mkdocs_literate_nav import parser


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
                # https://github.com/mkdocs/mkdocs/blob/ff0b726056/mkdocs/structure/nav.py#L113
                # Prevent the warning in case the user doesn't also end up including this page in
                # the final nav, maybe they want it only for the purpose of feeding to this plugin.
                mkdocs.structure.pages.Page(None, file, self.config)

                # https://github.com/mkdocs/mkdocs/blob/fa5aa4a26e/mkdocs/structure/pages.py#L120
                with open(file.abs_src_path, encoding="utf-8-sig") as f:
                    return f.read()
            # Not found, return None.

        config["nav"] = parser.markdown_to_nav(read_index_of_dir)

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
