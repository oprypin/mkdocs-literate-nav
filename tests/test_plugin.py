import pathlib

import mkdocs.structure.files
import pytest
from mkdocs.config.defaults import MkDocsConfig
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


@pytest.mark.skipif(
    not hasattr(mkdocs.structure.files, "InclusionLevel"), reason="requires MkDocs 1.5+"
)
@pytest.mark.parametrize(
    ("exclude_docs", "expected_inclusion"), [("SUMMARY.md", "EXCLUDED"), ("", "NOT_IN_NAV")]
)
def test_nav_file_with_undefined_inclusion(tmp_path_factory, exclude_docs, expected_inclusion):
    src_dir, dest_dir = map(tmp_path_factory.mktemp, ["src", "dest"])
    (src_dir / "SUMMARY.md").write_text("* [Foo](foo.md)\n", encoding="utf-8")
    (src_dir / "foo.md").write_text("# Foo\n", encoding="utf-8")

    config = MkDocsConfig()
    config.load_dict({"site_name": "test", "docs_dir": str(src_dir), "exclude_docs": exclude_docs})
    assert config.validate() == ([], [])

    # As if another plugin (e.g. mkdocs-gen-files) replaced the files without setting inclusion.
    files = Files(
        [
            File(fn, str(src_dir), str(dest_dir), use_directory_urls=True)
            for fn in ["SUMMARY.md", "foo.md"]
        ]
    )
    nav_file = files.get_file_from_path("SUMMARY.md")
    assert nav_file is not None
    assert nav_file.inclusion.name == "UNDEFINED"

    lit_nav = plugin.LiterateNavPlugin()
    lit_nav.load_config({})
    lit_nav.on_files(files, config)

    assert config.nav == [{"Foo": "foo.md"}]
    assert nav_file.inclusion.name == expected_inclusion
