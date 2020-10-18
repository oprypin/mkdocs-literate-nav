import mkdocs.config.base
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav

from mkdocs_literate_nav import parser, util


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (("nav_file", mkdocs.config.config_options.Type(str, required=True)),)

    def on_nav(self, nav, config, files):
        for page in nav.pages:
            page.previous_page = None
            page.next_page = None

        config["nav"] = parser.markdown_to_nav(
            files.get_file_from_path(self.config["nav_file"]).abs_src_path
        )
        return mkdocs.structure.nav.get_navigation(files, config)
