from mkdocs.structure.files import File


def pytest_assertrepr_compare(op, left, right):
    if isinstance(left, File) and isinstance(right, File) and op == "==":
        return [f"File({left.src_path}) != File({right.src_path})"]
    return None
