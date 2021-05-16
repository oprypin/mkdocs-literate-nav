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
            golden.get("nav"),
            files,
            nav_file_name=golden.get("nav_file_name") or "index.md",
            implicit_index=golden.get("implicit_index"),
        )
    assert output == golden.out["output"]


def _file_sort_key(f: File):
    parts = pathlib.PurePath(f.src_path).parts
    return tuple(chr(i != len(parts) - 1) + chr(f.name != "index") + p for i, p in enumerate(parts))
