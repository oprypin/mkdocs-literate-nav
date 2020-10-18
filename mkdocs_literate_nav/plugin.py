import pathlib

import mkdocs.config.base
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav

from mkdocs_literate_nav import parser


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (("nav_file", mkdocs.config.config_options.Type(str, required=True)),)

    def on_nav(self, nav, config, files):
        path = pathlib.Path(files.get_file_from_path(self.config["nav_file"]).abs_src_path)
        config["nav"] = parser.markdown_to_nav(path.read_text(encoding="utf-8"))

        # Reset the state from the internal `get_navigation` execution before running it again here.
        for file in files:
            file.page = None
        for page in nav.pages:
            page.previous_page = None
            page.next_page = None

        return mkdocs.structure.nav.get_navigation(files, config)
