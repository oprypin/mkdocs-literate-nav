import contextlib
import io
import re

import pytest
import yaml

from mkdocs_literate_nav import parser


class MultilineString(str):
    pass


yaml.add_representer(
    MultilineString,
    lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|"),
)


def pytest_collect_file(parent, path):
    if path.ext == ".yaml" and path.basename.startswith("test"):
        return TestFile.from_parent(parent, fspath=path)


class TestFile(pytest.File):
    def collect(self):
        yield TestItem.from_parent(self, name="test", file=self.fspath)


class TestItem(pytest.Item):
    def __init__(self, name, parent, file):
        super().__init__(name, parent)
        self.file = file
        self.spec = yaml.safe_load(file.open(encoding="utf-8"))
        self.actual = {
            k: MultilineString(v) for k, v in self.spec.items() if k not in ("output", "exception")
        }

    def runtest(self):
        try:
            self.actual["output"] = parser.markdown_to_nav(lambda root: self.spec["/" + root])
        except Exception as e:
            self.actual["exception"] = MultilineString(e)
        assert self.actual == self.spec


def pytest_addoption(parser):
    parser.addoption("--update-goldens", action="store_true", help="reset golden master benchmarks")


def pytest_runtest_teardown(item, nextitem):
    if item.config.getoption("--update-goldens") and isinstance(item, TestItem):
        with item.file.open("w", encoding="utf-8") as f:
            yml = yaml.dump(item.actual, f, sort_keys=False)
