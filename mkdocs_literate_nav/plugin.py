import mkdocs.config.base
import mkdocs.config.config_options
import mkdocs.plugins
import mkdocs.structure.files
import mkdocs.structure.nav

from mkdocs_literate_nav import parser, util


class LiterateNavPlugin(mkdocs.plugins.BasePlugin):
    config_scheme = (
        ("nav_file", mkdocs.config.config_options.File(exists=True)),
        ("exclude", mkdocs.config.config_options.Type(bool, default=False)),
    )

    def load_config(self, *args, **kwargs):
        errors, warnings = super().load_config(*args, **kwargs)
        if not self.config.get("nav_file"):
            error = mkdocs.config.base.ValidationError(
                "literate-nav plugin requires the nav_file parameter"
            )
            errors.append(("nav_file", error))
        return errors, warnings

    def on_files(self, files, config):
        result = []
        for f in files:
            if self.config["exclude"] and f.abs_src_path == self.config["nav_file"]:
                continue
            result.append(f)
        return mkdocs.structure.files.Files(result)

    def on_nav(self, nav, config, files):
        for page in nav.pages:
            page.previous_page = None
            page.next_page = None

        items = parser.markdown_to_nav(self.config["nav_file"])
        pages = []

        @util.collect
        def _convert_nav(items):
            for title, item in items:
                if isinstance(item, list):
                    section = mkdocs.structure.nav.Section(title, children=_convert_nav(item))
                    for child in section.children:
                        child.parent = section
                    yield section
                else:
                    page = mkdocs.structure.nav.Page(title, files.get_file_from_path(item), config)
                    if pages:
                        page.previous_page = pages[-1]
                        pages[-1].next_page = page
                    pages.append(page)
                    yield page

        items = _convert_nav(items)
        return mkdocs.structure.nav.Navigation(items, pages)
