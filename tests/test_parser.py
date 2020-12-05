import pytest
from mkdocs.structure.files import File, Files

from mkdocs_literate_nav import exceptions, parser, plugin


@pytest.mark.golden_test("markdown_to_nav/**/*.yml")
@pytest.mark.parametrize("use_directory_urls", [True, False])
def test_markdown_to_nav(tmp_path_factory, use_directory_urls, golden):
    src_dir, dest_dir = map(tmp_path_factory.mktemp, ["src", "dest"])

    files = [File(f, src_dir, dest_dir, use_directory_urls) for f in golden.get("files") or ()]
    files = Files(files)
    globber = plugin.MkDocsGlobber(files)
    get_md = lambda root: golden["navs"].get("/" + root)

    output = None
    with golden.may_raise(exceptions.LiterateNavError), golden.capture_logs(
        "mkdocs.plugins.mkdocs_literate_nav"
    ):
        output = parser.markdown_to_nav(get_md, globber)
    assert output == golden.out.get("output")
