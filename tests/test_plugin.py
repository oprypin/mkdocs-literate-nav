import pathlib

import pytest
from mkdocs.structure.files import File, Files

from mkdocs_literate_nav import exceptions, plugin


@pytest.mark.golden_test("nav/**/*.yml")
def test_nav(tmp_path_factory, golden):
    src_dir, dest_dir = map(tmp_path_factory.mktemp, ["src", "dest"])

    files = []
    for fn, content in (golden.get("files") or {}).items():
        path = src_dir / fn
        path.parent.mkdir(parents=True, exist_ok=True)
        if content is not None:
            path.write_text(content, encoding="utf-8")
        files.append(File(fn, src_dir, dest_dir, use_directory_urls=len(golden.path.name) % 2))
    assert [f.src_path for f in sorted(files, key=file_sort_key)] == [f.src_path for f in files]
    files = Files(files)

    output = None
    with golden.may_raise(exceptions.LiterateNavError):
        with golden.capture_logs("mkdocs.plugins.mkdocs_literate_nav"):
            output = plugin.resolve_directories_in_nav(
                golden.get("nav"),
                files,
                nav_file_name=golden.get("nav_file_name") or "SUMMARY.md",
                implicit_index=golden.get("implicit_index"),
            )
    assert output == golden.out.get("output")


# https://github.com/oprypin/mkdocs-gen-files/blob/71a4825d5c/mkdocs_gen_files/editor.py#L16
def file_sort_key(f: File):
    parts = pathlib.PurePath(f.src_path).parts
    return tuple(
        chr(f.name != "index" if i == len(parts) - 1 else 2) + p for i, p in enumerate(parts)
    )
