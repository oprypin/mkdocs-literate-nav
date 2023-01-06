## Literate nav syntax

The literate nav file must be a Markdown file, which can contain arbitrary content, but the **last-encountered Markdown list** in it will be used to determine the navigation. It must adhere to [specific rules](#nav-list-syntax), otherwise an error will be generated.

### Explicit nav mark

If any line in the Markdown file has the exact content "`<!--nav-->`", that changes the choice of nav list for that file to instead be the first-encountered list after such a line.

### Nav list syntax

!!! example "SUMMARY.md"

    ```markdown
    * [First list item](some-page.md)
    * Subsection title
        * [Something](subdirectory/something.md)
        * subdirectory/*.md
    * [Other directory](other/)
    ```

The navigation list must be a top-level [Markdown list](https://daringfireball.net/projects/markdown/syntax#list), regardless if it's an ordered list or not. It can contain other sub-lists, which are used as sub-directories for the nav.

To include a page into the nav, write a [Markdown link](https://daringfireball.net/projects/markdown/syntax#link) such as `[Page title](path/to/some-page.md)`. Unlike with the [native nav](#mkdocs-native-nav), a title is mandatory; bare paths are an error (unless they contain an asterisk; see below).

Links in the nav file directly under the root [`docs` dir][docs_dir] are relative to the `docs` dir, and for nav files that are in a subdirectory, links are relative to that subdirectory (generally referred to as "current" directory). Links can refer to files that are in other directories, both below (`sub/dir/foo.md`) and above (`../foo.md`) the current directory -- though the latter is not as well supported. The forward slash `/` must be used as the path separator.

To add a sub-section into a nav, make a list item that is not a link (so its text becomes the section title) and start a nested list under it (so its content turns into the section nav). The rules apply recursively to that list.

The parser makes some effort to allow *and strip* other inline Markdown markup (e.g. italics), but this is generally unsupported.

### Wildcards

Bare paths that contain an `*` asterisk are recognized as [wildcards](#wildcards). Asterisks are special *only* in bare items; they don't do anything inside a Markdown link.

A wildcard item, whenever encountered in a list, will be replaced with every file *and directory* that matches it and is not mentioned in the nav explicitly already *and* hasn't been matched by any preceding wildcard items. It is possible to select only directories by adding a trailing slash, like `*/`. And to distinguish files, you have to rely on them having a file extension, and write e.g. `*.md`.

Wildcards can traverse to subdirectories and parent directories as well. However, the directly matching items will be included *flatly* into the current nav list -- though if a *directory* matches, its sub-items will not be flattened.

Currently the only officially supported special character in a wildcard is an `*` asterisk. It indicates that there can be 0 or more arbitrary characters (excluding the path separator) in its place.

Resolution of wildcards is done in a particular order, depth-first from the perspective of the final layout of the nav. The reason that the order is important is that *literate-nav* always tries to exclude items from a wildcard that was already mentioned elsewhere in the nav, so the items are not duplicated. If the two relevant occurrences are somewhere in the same directory tree (one nav section is a parent of the other), the detection will always just work. If they are in separate directory trees, order starts to matter: only items mentioned "earlier" (in top-to-bottom reading order) will be omitted from wildcards occurring "later". The same ordering applies if there are two wildcards competing for the same items: only the "earlier" one will contain those items.

#### Subdirectory cross-link

If a link's destination ends with a `/` slash, it is instead recognized as a [subdirectory cross-link](#subdirectory-cross-link).

A link that leads to a path ending with `/` is understood to be a directory cross-link. If such a directory actually exists relative to the current directory, the nav for it is inserted into this place. If there is no such subdirectory, the link text is kept as is and is likely invalid in the end.

If that subdirectory has no [nav file](#nav_file), then writing a directory cross-link means including that directory as a sub-section that recursively includes all the directory's items. I.e. the following two approaches are fully equivalent then:

```markdown
* [Foo](foo/)
```

```markdown
* Foo
  * foo/*
```

But if that subdirectory *does* have a nav file, then that is resolved in the context of that subdirectory and put back into the nav under the subsection.



## MkDocs native nav

If there is no literate nav file in the [`docs` dir][docs_dir], this plugin will fall back to using the [normal `nav:` defined in the file `mkdocs.yml`](https://www.mkdocs.org/user-guide/writing-your-docs/#configure-pages-and-navigation). But its items gain extended syntax.

!!! example "mkdocs.yml"
    ```yaml
    nav:
    - Foo: foo.md
    - Usual:
        - usual/a.md
        - usual/b.md
    - '*.md'
    - Subdir: subdir/
    ```

In this example only the last two items are special.

Wildcards (items without a title that have an asterisk in them) get replaced by files that they match, relative to the root [`docs` dir][docs_dir]. The resolution rules are the same as [wildcards in a literate nav](#wildcards).

[Subdirectory cross-link](#subdirectory-cross-link) items (items with a title and a link that ends with a slash) get replaced by the literate nav for the linked directory (if it exists), under a section with this title.

## MkDocs plugin

!!! example "mkdocs.yml"
    ```yaml
    plugins:
      - literate-nav:
          nav_file: SUMMARY.md
          implicit_index: false
          tab_length: 4
    ```

### Config

#### `nav_file`

*string, default `'SUMMARY.md'`*

The name of the file to read to determine the navigation for a particular directory under [`docs_dir`][docs_dir]. E.g. if the directory `docs/foo/bar/` is referenced, the file `docs/foo/bar/SUMMARY.md` will be read for it.

This file must contain [a Markdown list](#literate-nav-syntax) that defines the navigation for that directory. If for a particular directory there is no such file, the navigation will be inferred automatically, following [normal MkDocs rules](https://www.mkdocs.org/user-guide/writing-your-docs/#configure-pages-and-navigation). If there is no such file for the [root `docs_dir`][], the nav can fall back to [MkDocs native nav](#mkdocs-native-nav).

Although there can be several such files throughout the site, the choice of the file name is global and not modifiaable on a case-by-case basis.

#### `implicit_index`

*boolean, default `false`*

If a directory has a file named [`index.md` or `README.md`](https://www.mkdocs.org/user-guide/writing-your-docs/#index-pages), but the literate nav for that directory that never includes it, it will be inserted as the first item of the nav.

This is important when using directory cross-linking, which otherwise makes it impossible to specify a *[section-index][]* page for a subdirectory.

#### `tab_length`

*integer, default `4`*

By default (like in MkDocs), lists need to be indented by 4 spaces. The more modern style is 2 spaces, though.

You can change the indentation just for the extension, but that will not affect MkDocs' rendering. If you want to change both at once, install [mdx_truly_sane_lists](https://github.com/radude/mdx_truly_sane_lists) and use it through `markdown_extensions`, instead of this option. See example below.

#### `markdown_extensions`

*list of mappings, [same as MkDocs](https://www.mkdocs.org/user-guide/configuration/#markdown_extensions)*

!!! example "mkdocs.yml"
    ```yaml
    plugins:
      - literate-nav:
          markdown_extensions:
            - mdx_truly_sane_lists

    markdown_extensions:
      - mdx_truly_sane_lists
    ```

[mkdocs-nav]: https://www.mkdocs.org/user-guide/writing-your-docs/#configure-pages-and-navigation
[docs_dir]: https://www.mkdocs.org/user-guide/configuration/#docs_dir
