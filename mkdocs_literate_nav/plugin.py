import os.path
import pathlib
from typing import Optional

import mkdocs.config
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav

from mkdocs_literate_nav import parser


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (("nav_file", mkdocs.config.config_options.Type(str)),)

    def _find_index_of_dir(
        self, files: mkdocs.structure.files.Files, path: str = ""
    ) -> mkdocs.structure.files.File:
        """Finds the directory's index (or nav if specified) Markdown file."""
        if self.config["nav_file"]:
            return files.get_file_from_path(os.path.join(path, self.config["nav_file"]))
        for f in files:
            if os.path.split(f.src_path)[0] == path and f.name == "index":
                return f

    def on_nav(
        self,
        nav: mkdocs.structure.nav.Navigation,
        config: mkdocs.config.Config,
        files: mkdocs.structure.files.Files,
    ) -> mkdocs.structure.nav.Navigation:
        del nav

        def read_index_of_dir(path: str) -> Optional[str]:
            file = self._find_index_of_dir(files, path)
            if file:
                # https://github.com/mkdocs/mkdocs/blob/fa5aa4a26efc2a0dc3878b41920eaa39afc8929b/mkdocs/structure/pages.py#L120
                with open(file.abs_src_path, encoding="utf-8-sig") as f:
                    return f.read()

        config["nav"] = parser.markdown_to_nav(read_index_of_dir)

        # Reset the state from the internal `get_navigation` execution before running it again here.
        for file in files:
            file.page = None

        return mkdocs.structure.nav.get_navigation(files, config)
