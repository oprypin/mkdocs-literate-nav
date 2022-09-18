#!/bin/sh
set -e

cd "$(dirname "$0")/.."

with_groups() {
    echo "::group::$@"
    "$@" && echo "::endgroup::"
}

"$@" autoflake -i -r --remove-all-unused-imports --remove-unused-variables mkdocs_literate_nav tests
"$@" isort -q mkdocs_literate_nav tests
"$@" black -q mkdocs_literate_nav tests
"$@" pytest -q
python -c 'import sys, os; sys.exit((3,8) <= sys.version_info < (3,11) and os.name == "posix")' ||
"$@" pytype mkdocs_literate_nav
