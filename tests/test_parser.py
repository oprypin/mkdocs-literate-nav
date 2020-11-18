import pytest

from mkdocs_literate_nav import exceptions, parser


@pytest.mark.golden_test("markdown_to_nav/**/*.yml")
def test_markdown_to_nav(golden):
    output = None
    with golden.may_raise(exceptions.LiterateNavError), golden.capture_logs(
        "mkdocs.plugins.mkdocs_literate_nav"
    ):
        output = parser.markdown_to_nav(lambda root: golden["navs"].get("/" + root))
    assert output == golden.out.get("output")
