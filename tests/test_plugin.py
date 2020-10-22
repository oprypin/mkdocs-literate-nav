import pytest
from mkdocs.structure.files import File, Files

from mkdocs_literate_nav import plugin


@pytest.mark.parametrize("use_directory_urls", [True, False])
def test_find_index_of_dir(tmp_path_factory, use_directory_urls):
    src_dir, dest_dir = map(tmp_path_factory.mktemp, ["src", "dest"])
    file_names = [
        " README.md",
        "README.md ",
        "index.md",
        "bad/index.html",
        "bad/foo.md",
        "bad/foo.index.md",
        "both1/index.md",
        "both1/README.md",
        "both2/readme.md",
        "both2/index.md",
        "a/a/a/a/a/README.md",
    ]
    files = {f: File(f, src_dir, dest_dir, use_directory_urls) for f in file_names}
    files_o = Files(list(files.values()))

    assert plugin._find_index_of_dir({}, files_o, "") == files["index.md"]
    assert plugin._find_index_of_dir({}, files_o, "nonexistent") is None
    assert plugin._find_index_of_dir({}, files_o, "bad") is None
    assert plugin._find_index_of_dir({}, files_o, "bad/foo") is None
    assert plugin._find_index_of_dir({}, files_o, "bad/foo.md") is None
    assert plugin._find_index_of_dir({}, files_o, "both1") == files["both1/README.md"]
    assert plugin._find_index_of_dir({}, files_o, "both2") == files["both2/index.md"]
    assert plugin._find_index_of_dir({"nav_file": "foo.md"}, files_o, "bad") == files["bad/foo.md"]
    assert plugin._find_index_of_dir({"nav_file": "foo.md"}, files_o, "both2") is None
    assert plugin._find_index_of_dir({"nav_file": "a"}, files_o, "a/a/a/a") is None
    assert plugin._find_index_of_dir({}, files_o, "a/a/a/a/a") == files["a/a/a/a/a/README.md"]
    assert plugin._find_index_of_dir({}, files_o, "a/a/a/a/a/a") is None
