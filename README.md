# mkdocs-literate-nav

### [Plugin][] for [MkDocs][] to specify the navigation in Markdown instead of YAML

[![PyPI](https://img.shields.io/pypi/v/mkdocs-literate-nav)](https://pypi.org/project/mkdocs-literate-nav/)
[![GitHub](https://img.shields.io/github/license/oprypin/mkdocs-literate-nav)](LICENSE.md)
[![GitHub Workflow Status](https://img.shields.io/github/workflow/status/oprypin/mkdocs-literate-nav/CI)](https://github.com/oprypin/mkdocs-literate-nav/actions?query=event%3Apush+branch%3Amaster)

```shell
pip install mkdocs-literate-nav
```

Works well with **[section-index][]**. Supplants **[awesome-pages][]**.

[mkdocs]: https://www.mkdocs.org/
[plugin]: https://www.mkdocs.org/user-guide/plugins/
[section-index]: https://github.com/oprypin/mkdocs-section-index
[awesome-pages]: https://github.com/lukasgeiter/mkdocs-awesome-pages-plugin

## Usage

Activate the plugin in **mkdocs.yml**:

```yaml
plugins:
  - search
  - mkdocs-literate-nav:
      nav_file: SUMMARY.md
```

and **drop** the `nav` section if it's present there; it will be ignored now.

<table><tr>
<td>To get this navigation,</td>
<td>create the file <b>SUMMARY.md</b>:</td>
<td>(old YAML equivalent:)</td>
</tr><tr><td>

* [Frob](#index.md)
* [Baz](#baz.md)
* [Borgs](#borgs/index.md)
    * [Bar](#borgs/bar.md)
    * [Foo](#borgs/foo.md)

</td><td>

```markdown
* [Frob](index.md)
* [Baz](baz.md)
* [Borgs](borgs/index.md)
    * [Bar](borgs/bar.md)
    * [Foo](borgs/foo.md)
```

</td><td>

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - Borgs:
    - borgs/index.md
    - Bar: borgs/bar.md
    - Foo: borgs/foo.md
```

</td></tr></table>

Note that, the way we wrote the Markdown, a section seems to also have a page associated with it. MkDocs doesn't actually support that, and neither is it representable in YAML directly, so the plugin tries to do the next best thing: include the link as the first page of the section. However, this structure is perfectly suited for the **[section-index][]** plugin, which actually makes this work. Or you could just *not* associate a link with sections:

<table><tr>
<td>To get this navigation,</td>
<td>create the file <b>SUMMARY.md</b>:</td>
<td>(old YAML equivalent:)</td>
</tr><tr><td>

* [Frob](#index.md)
* [Baz](#baz.md)
* Borgs
    * [Bar](#borgs/bar.md)
    * [Foo](#borgs/foo.md)

</td><td>

```markdown
* [Frob](index.md)
* [Baz](baz.md)
* Borgs
    * [Bar](borgs/bar.md)
    * [Foo](borgs/foo.md)
```

</td><td>

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - Borgs:
    - Bar: borgs/bar.md
    - Foo: borgs/foo.md
```

</td></tr></table>

#### Nav cross-link

But why stop there? Each directory can have its own decoupled navigation list (see how the trailing slash initiates a nav cross-link):

<table><tr>
<td>To get this navigation,</td>
<td>create the file <b>SUMMARY.md</b>:</td>
<td>(old YAML equivalent:)</td>
</tr><tr><td rowspan="3">

* [Frob](#index.md)
* [Baz](#baz.md)
* Borgs
    * [Bar](#borgs/bar.md)
    * [Foo](#borgs/foo.md)

</td><td>

```markdown
* [Frob](index.md)
* [Baz](baz.md)
* [Borgs](borgs/)
```

</td><td rowspan="3">

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - Borgs:
    - Bar: borgs/bar.md
    - Foo: borgs/foo.md
```

</td></tr><tr>
<td>and the file <b>borgs/SUMMARY.md</b>:</td>
</tr><tr><td>

```markdown
* [Bar](bar.md)
* [Foo](foo.md)
```

</td></tr></table>

Or perhaps you don't care about the order of the pages under the borgs/ directory? Just drop the file <b>borgs/SUMMARY.md</b> and let it be inferred.

The fallback behavior follows the [default behavior of MkDocs when nav isn't specified][nav-gen], except that you can opt out on a per-directory basis.

[nav-gen]: https://www.mkdocs.org/user-guide/writing-your-docs/#configure-pages-and-navigation

Is your directory structure not so tidy? That's not a problem, the implicit nav will not add duplicates of pages already mentioned elsewhere (but you can always add duplicates explicitly...)

#### `nav_file`

We've been using **SUMMARY.md** as the name of the file that specifies the nav, but naturally, you can use any other file name. The plugin takes care to not let MkDocs complain if you don't end up using the nav document as an actual page of your doc site.

Or maybe you want the opposite -- make the nav page very prominent? You can actually use the index page, **README.md**, for the nav (and that's even the default)! Why would one do this? Well, GitHub (or another source hosting) also displays the Markdown files, and it's quite a nice perk to show off your navigation right in the index page of a directory. What's that, you ask? If the index page is taken up by navigation, we can't put any other content there, can we? Actually, we can! The nav list can just be put at the bottom of the page that also has whatever other content before that.

#### Explicit nav mark

If the plugin is confused where on the page the nav is, please precede the Markdown list with this HTML comment (verbatim) on a line of its own:

```markdown
<!--nav-->
```

### Migrating from GitBook?

It might be very easy! Just beware of the stricter Markdown parser; it will *not* accept 2-space indentation for sub-lists.

And use this for **mkdocs.yml**:

<table><tr><td>

```yaml
use_directory_urls: false
```
```yaml
plugins:
  - search
  - same-dir
  - section-index
  - literate-nav:
      nav_file: SUMMARY.md
```

</td><td>

```yaml
theme:
  name: material
```
```yaml
markdown_extensions:
  - pymdownx.highlight
  - pymdownx.magiclink
  - pymdownx.superfences
```

</td></tr></table>
