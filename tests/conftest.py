import contextlib
import io
import re

import pytest
import testfixtures
import yaml
from mkdocs.structure.files import File

from mkdocs_literate_nav import parser


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, File) and isinstance(right, File) and op == "==":
        return [f"File({left.src_path}) != File({right.src_path})"]


class MultilineString(str):
    pass


yaml.add_representer(
    MultilineString,
    lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|"),
)


def pytest_collect_file(parent, path):
    if path.ext == ".yml" and path.basename.startswith("test"):
        return TestFile.from_parent(parent, fspath=path)


class TestFile(pytest.File):
    def collect(self):
        yield TestItem.from_parent(self, name="test", file=self.fspath)


class TestItem(pytest.Item):
    def __init__(self, name, parent, file):
        super().__init__(name, parent)
        self.file = file
        self.spec = yaml.safe_load(file.open(encoding="utf-8"))
        self.actual = {k: MultilineString(v) for k, v in self.spec.items() if k.startswith("/")}

    @testfixtures.log_capture(
        "mkdocs.plugins.mkdocs_literate_nav", attributes=("levelname", "getMessage")
    )
    def runtest(self, capture):
        try:
            self.actual["output"] = parser.markdown_to_nav(lambda root: self.spec.get("/" + root))
        except Exception as e:
            self.actual["exception"] = {type(e).__name__: MultilineString(e)}
        if capture.actual():
            self.actual["logs"] = [":".join(log) for log in capture.actual()]
        assert self.actual == self.spec


def pytest_addoption(parser):
    parser.addoption("--update-goldens", action="store_true", help="reset golden master benchmarks")


def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption("--update-goldens") and isinstance(item, TestItem):
        with item.file.open("w", encoding="utf-8") as f:
            yml = yaml.dump(item.actual, f, sort_keys=False)
