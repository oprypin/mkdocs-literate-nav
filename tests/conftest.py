import pytest_golden.yaml
from mkdocs.structure.files import File

from mkdocs_literate_nav import parser


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, File) and isinstance(right, File) and op == "==":
        return [f"File({left.src_path}) != File({right.src_path})"]


pytest_golden.yaml.add_representer(
    parser.Wildcard, lambda dumper, data: dumper.represent_scalar("!Wildcard", data)
)
pytest_golden.yaml.add_constructor("!Wildcard", lambda loader, node: parser.Wildcard(node.value))
