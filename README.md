# mkdocs-literate-nav

**[Plugin][] for [MkDocs][] to specify the navigation in Markdown instead of YAML**

[![PyPI](https://img.shields.io/pypi/v/mkdocs-literate-nav)](https://pypi.org/project/mkdocs-literate-nav/)
[![GitHub](https://img.shields.io/github/license/oprypin/mkdocs-literate-nav)](https://github.com/oprypin/mkdocs-literate-nav/blob/master/LICENSE.md)
[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/oprypin/mkdocs-literate-nav/ci.yml.svg)](https://github.com/oprypin/mkdocs-literate-nav/actions?query=event%3Apush+branch%3Amaster)

```shell
pip install mkdocs-literate-nav
```

Works well with **[section-index][]** and **[gen-files][]**. Supplants **[awesome-pages][]**.

[mkdocs]: https://www.mkdocs.org/
[plugin]: https://www.mkdocs.org/user-guide/plugins/
[section-index]: https://oprypin.github.io/mkdocs-section-index/
[gen-files]: https://oprypin.github.io/mkdocs-gen-files/
[awesome-pages]: https://github.com/lukasgeiter/mkdocs-awesome-pages-plugin

## Usage

Activate the plugin in **mkdocs.yml**:

```yaml
plugins:
  - search
  - literate-nav:
      nav_file: SUMMARY.md
```

and **drop** the `nav` section if it's present there; it will be ignored now. ([Unless you want to keep it?](#hybrid-nav))

<table markdown="1"><tr>
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

IMPORTANT: The nav file must be put inside the [`docs` directory][docs_dir] -- at the root of it.

So, the plugin lets you specify your site's navigation with lists of links that are parsed according to normal Markdown rules.

Note that, the way we wrote the Markdown, a section seems to also have a page associated with it. MkDocs doesn't actually support that, and neither is it representable in YAML directly, so the plugin tries to do the next best thing: include the link as the first page of the section. However, this structure is perfectly suited for the *[section-index][]* plugin, which actually makes that work. Or you could just *not* associate a link with sections:

<table markdown="1"><tr>
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

**[See syntax details about literate nav files.](https://oprypin.github.io/mkdocs-literate-nav/reference.html)**

You can find more examples of the "literate nav" syntax [in the testcases directory](https://github.com/oprypin/mkdocs-literate-nav/tree/master/tests/nav).

### Nav cross-link

But why stop there? Each directory can have its own decoupled navigation list (see how the trailing slash initiates a nav cross-link):

<table markdown="1"><tr>
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

> NOTE: The nav file in the subdirectory is picked up *only* because its directory is explicitly mentioned in a parent nav file. **SUMMARY.md** (generally [`nav-file`](customizing-nav_file)) files are **not** picked up implicitly (only the root nav file is "implicit").
>
> So you might say that the nav construction approach is exactly the opposite from the *[awesome-pages][]* plugin.
>
> That said, an [inferred cross-linked directory](#inferred-sub-directory) (whether directly or through [wildcards](#wildcards)) gets resolved recursively, so that way you actually go back to implicit resolution.

#### Inferred sub-directory

Or perhaps you don't care about the order of the pages under the **borgs/** directory? Just drop the file __borgs/SUMMARY.md__ and let it be inferred (recursively, if applicable). For our particular example, the final result would be the same.

The fallback behavior follows the [default behavior of MkDocs when nav isn't specified][mkdocs-nav], except that you can leave out only some directory trees, rather than an all-or-nothing choice.

### Wildcards

Between the two extremes of entirely specifying a nav and entirely inferring it, there's the option of applying wildcards.

Instead of putting links like `[Foo 1](foo_1.md)`, `[Foo 2](foo_2.md)` into the nav list, you can write a wildcard item: `foo_*.md` (bare, not as a link). The asterisk indicates that any number of characters can go there, and the file name has to match the rest of the pattern.

A wildcard item is always required to have at least one `*` asterisk in it, because if it doesn't, then it's *just* a bare item, which are disallowed.

**[See details about wildcards.](https://oprypin.github.io/mkdocs-literate-nav/reference.html#wildcards)**

So this can be used to fully specify order for items that matter and apply wildcards for all other cases. Example:

<table markdown="1"><tr>
<td>By writing this literate nav file,</td>
<td>you may get a nav like this:</td>
<td>(assuming the files exist:)</td>
</tr><tr><td>

```markdown
- [Welcome](index.md)
- Usage
    - [Foo](usage/foo.md)
    - usage/*.md
- */
- *.md
- [API docs](api/)
- [License](license.md)
```

</td><td>

```yaml
- Welcome: index.md
- Usage:
    - Foo: usage/foo.md
    - usage/bar.md
    - usage/baz.md
- Tips:
    - tips/other-stuff.md
    - tips/stuff.md
- changelog.md
- credits.md
- API docs:
    - api/Foo.md
    - Bar:
        - api/Bar/index.md
        - api/Bar/Baz.md
- License: license.md
```

</td><td>

* index.md
* changelog.md
* credits.md
* usage / bar.md
* usage / baz.md
* usage / foo.md
* tips / stuff.md
* tips / other-stuff.md
* api / Foo.md
* api / Bar / index.md
* api / Bar / Baz.md

</td></tr></table>

TIP: Speaking of API docs... Want to fine-tune file ordering in a large directory tree? Check out [integrations with other plugins](#extras).

The paths are relative to the directory that the nav file is in. Matching files in subdirectories also works, in both ways: `*/foo.md` and `foo/*.md`.

As it's impossible for a user to specify the titles of items produced by a wildcard, they have to be inferred, based on [normal rules of MkDocs][mkdocs-nav].

> TIP: The ordering of items matches MkDocs' default, so first go all files, alphabetically (but with the index file first), then all directories. But, as an example, you could actually swap that, by writing:
>
> ```markdown
> - */
> - *
> ```

You can find more examples of the wildcard syntax [in the testcases directory](https://github.com/oprypin/mkdocs-literate-nav/tree/master/tests/nav/wildcard).

### Customizing `nav_file`

We've been using **SUMMARY.md** as the name of the file that specifies the nav (actually that is also the default value of `nav_file`), but naturally, you can use any other file name.

**[See details about the `nav_file` config.](https://oprypin.github.io/mkdocs-literate-nav/reference.html#nav_file)**

The plugin takes care to not let MkDocs complain if you don't end up using the nav document as an actual page of your doc site.

#### Show off your nav on the front page

Or maybe you want the opposite -- make the nav page very prominent? You can actually use the index page, **README.md**, for the nav!

Why would one do this? Well, GitHub (or another source hosting) also displays the Markdown files, and it's quite a nice perk to show off your navigation right in the index page of a directory. Of course, then you'd probably refrain from using [wildcards](#wildcards). [Directory cross linking](#nav-cross-link) still looks great, though.

What's that, you ask? If the index page is taken up by navigation, we can't put any other content there, can we? Actually, we can! The nav list can just be put at the bottom of the page that also has whatever other content before that.

[See an example of all this in action](https://github.com/oprypin/crsfml/tree/master/docs/tutorials)

#### Explicit nav mark

If the plugin is confused where in the document the nav is, or if you want to explicitly put it in a particular location, please precede the Markdown list with this HTML comment (verbatim) on a line of its own:

```html
<!--nav-->
```

### Hybrid nav

Do the features of this plugin interest you but you're not on board with the idea of migrating your whole nav?

You can actually keep using [MkDocs' own nav specification][mkdocs-nav] at the root, *but* defer only some subdirectories to the *literate-nav* plugin. In that case make sure to *not* put a nav file at the [`docs` root][docs_dir], otherwise the native nav will be ignored.

<table markdown="1"><tr>
<td>To get this navigation,</td>
<td>put this into <b>mkdocs.yml</b>:</td>
<td>(old YAML equivalent:)</td>
</tr><tr><td rowspan="3">

* [Frob](#index.md)
* [Baz](#baz.md)
* Borgs
    * [Bar](#borgs/bar.md)
    * [Foo](#borgs/foo.md)

</td><td>

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - Borgs: borgs/
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
<td>& create the file <b>borgs/SUMMARY.md</b>:</td>
</tr><tr><td>

```markdown
* [Bar](bar.md)
* [Foo](foo.md)
```

</td></tr></table>

The syntax to defer to a subdirectory, just like [in a literate nav](#nav-cross-link), is to write an item that *ends* with a slash.

NOTE: There is no way to use a YAML nav for a subdirectory, only a literate nav can be deferred.

Wildcards also work very similarly.

**[See details about syntax additions for MkDocs native nav.](https://oprypin.github.io/mkdocs-literate-nav/reference.html#mkdocs-native-nav)**

You can find examples of the hybrid nav syntax [in the testcases directory](https://github.com/oprypin/mkdocs-literate-nav/tree/master/tests/nav/hybrid).

#### MkDocs native nav with inferred subdirectories

As before, whenever you have the option of using a literate nav file for a sub-directory, you can also *not* put any nav file there and infer the sub-directory instead. So, *not* creating the file **borgs/SUMMARY.md** would have yielded the same result in the above example.

So basically, you can use the *literate-nav* plugin just for its ability to infer only sub-directories, without ever writing any actual "literate navs".

#### Details about hybrid nav

As a final example, note that there are two ways to include a subdirectory, with significant difference:

<table markdown="1"><tr>
<td>To get this navigation,</td>
<td>put this into <b>mkdocs.yml</b>:</td>
<td>To get this navigation,</td>
<td>put this into <b>mkdocs.yml</b>:</td>
</tr><tr><td>

* [Frob](#index.md)
* [Baz](#baz.md)
* Borgs
    * [Bar](#borgs/bar.md)
    * [Foo](#borgs/foo.md)

</td><td>

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - Borgs: borgs/
```

</td><td>

* [Frob](#index.md)
* [Baz](#baz.md)
* [Bar](#borgs/bar.md)
* [Foo](#borgs/foo.md)

</td><td>

```yaml
nav:
  - Frob: index.md
  - Baz: baz.md
  - borgs/*
```

</td></tr></table>

So, a directory item with a title becomes a section titled as such. And a wildcard (which can't have a title specified) gets inlined into the existing section. This simple example has no sub-sub-directories, but the relative subdirectory structure would be preserved in both cases if it did.

### Extras

#### Programmatic control over the nav

Let's say you need the ability to infer nav for a sub-directory, but are unhappy with the default naming/layout behavior, and you don't want to write all that out manually either. Then, definitely check out the ***[gen-files][]* plugin**. Its normal usage is to programmatically add files to the site during the build, but that also includes literate nav files! Moreover, you don't even have to teach your program to write Markdown. There's a more direct integration: `mkdocs_gen_files.Nav.build_literate_nav`.

[See an example that generates both the files and the navigation covering them](https://github.com/mkdocstrings/mkdocstrings/blob/5802b1ef5ad9bf6077974f777bd55f32ce2bc219/docs/gen_doc_stubs.py#L25).

#### Indent lists by 2 spaces, not 4

Configure it through [tab_length](https://oprypin.github.io/mkdocs-literate-nav/reference.html#tab_length) or [markdown_extensions](https://oprypin.github.io/mkdocs-literate-nav/reference.html#markdown_extensions)

#### Migrating from GitBook?

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



[mkdocs-nav]: https://www.mkdocs.org/user-guide/writing-your-docs/#configure-pages-and-navigation
[docs_dir]: https://www.mkdocs.org/user-guide/configuration/#docs_dir
