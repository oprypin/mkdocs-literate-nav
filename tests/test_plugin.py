import pathlib

import pytest
from mkdocs.structure.files import File, Files

from mkdocs_literate_nav import plugin


@pytest.mark.golden_test("resolve_directories_in_nav/**/*.yml")
@pytest.mark.parametrize("use_directory_urls", [True, False])
def test_resolve_directories_in_nav(tmp_path_factory, use_directory_urls, golden):
    src_dir, dest_dir = map(tmp_path_factory.mktemp, ["src", "dest"])
    files = []
    for fn, content in golden["files"].items():
        path = src_dir / fn
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        files.append(File(fn, src_dir, dest_dir, use_directory_urls))
    assert [f.src_path for f in sorted(files, key=_file_sort_key)] == [f.src_path for f in files]
    files = Files(files)

    with golden.capture_logs("mkdocs.plugins.mkdocs_literate_nav"):
        output = plugin.resolve_directories_in_nav(
            golden.get("nav"), files, golden.get("nav_file_name"), golden.get("implicit_index")
        )
    assert output == golden.out["output"]


def _file_sort_key(f: File):
    parts = pathlib.PurePath(f.src_path).parts
    return tuple(chr(i != len(parts) - 1) + chr(f.name != "index") + p for i, p in enumerate(parts))


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

    assert plugin.find_index_of_dir(files_o, "") == files["index.md"]
    assert plugin.find_index_of_dir(files_o, "nonexistent") is None
    assert plugin.find_index_of_dir(files_o, "bad") is None
    assert plugin.find_index_of_dir(files_o, "bad/foo") is None
    assert plugin.find_index_of_dir(files_o, "bad/foo.md") is None
    assert plugin.find_index_of_dir(files_o, "both1") == files["both1/README.md"]
    assert plugin.find_index_of_dir(files_o, "both2") == files["both2/index.md"]
    assert plugin.find_index_of_dir(files_o, "bad", "foo.md") == files["bad/foo.md"]
    assert plugin.find_index_of_dir(files_o, "both2", "foo.md") is None
    assert plugin.find_index_of_dir(files_o, "a/a/a/a", "a") is None
    assert plugin.find_index_of_dir(files_o, "a/a/a/a/a") == files["a/a/a/a/a/README.md"]
    assert plugin.find_index_of_dir(files_o, "a/a/a/a/a/a") is None
