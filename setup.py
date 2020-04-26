import setuptools

setuptools.setup(
    name="mkdocs-literate-nav",
    install_requires=["mkdocs>=1"],
    packages=["mkdocs_literate_nav"],
    entry_points={
        "mkdocs.plugins": [
            "literate-nav = mkdocs_literate_nav.plugin:LiterateNavPlugin"
        ]
    },
)
