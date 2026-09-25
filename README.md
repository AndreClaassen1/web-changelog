# web-changelog

A changelog page and a "What's new" dialog for Flask applications. The
application's `CHANGELOG.md` is read at runtime; on the first visit after an
update, a dialog shows what changed since the version the visitor saw last.

The library is a port of the Swift package `AppChangelog`, which does the same
for macOS and iOS apps.

## Language

The user interface is **German by default**, and so is the Python API
(`Changelogs(pfad=..., vokabular=...)`, `pruefe()`, `Vokabular`). Every visible
text can be changed:

- **Section labels** ("Hinzugefügt", "Neu", "Behoben", ...) come from a
  `Vokabular`. Pass your own with English labels, see [Sections](#sections).
- **Fixed texts** of the page and the dialog ("Neuigkeiten", "Neu in ...",
  "Alle Änderungen ansehen", "Verstanden", "aktuell", the empty-state message)
  live in the bundled Jinja templates. An application overrides any of them by
  placing a file with the same name under its own `templates/web_changelog/`
  folder; the application loader wins over the blueprint loader. The files are
  `layout.html`, `seite.html`, `dialog.html` and `makros.html`.
- **The URL of the page** defaults to `/neuigkeiten` and is set with
  `pfad_seite`.

The parser understands German and English section headings (`Added`,
`Changed`, `Fixed`, ... as well as `Hinzugefügt`, `Geändert`, `Behoben`, ...).

## Installation

The package is not on PyPI yet. Install it from a source checkout:

```bash
pip install .
```

It requires Python 3.10 or newer and Flask 3.

## Integration into a Flask app

```python
from pathlib import Path
from web_changelog import Changelogs, VOKABULAR_ANWENDER

changelogs = Changelogs(
    app,
    pfad=Path(__file__).resolve().parent / "CHANGELOG.md",
    vokabular=VOKABULAR_ANWENDER,
    pfad_seite="/neuigkeiten",
    app_name="My App",
)
```

Add two calls to the application's base layout:

```jinja
{{ wc_head() }}        {# inside <head>: stylesheet #}
{{ wc_whatsnew() }}    {# before </body>: dialog, empty when nothing is pending #}
```

The page is now served at `/neuigkeiten` and the dialog is active. The
`Changelogs` object also supports the application factory pattern: create it
without `app` and call `init_app(app)` later.

## Configuration

| Parameter | Default | Meaning |
|---|---|---|
| `pfad` | required | Path to the `CHANGELOG.md` |
| `vokabular` | `VOKABULAR_KAC` | Section vocabulary, see [Sections](#sections) |
| `pfad_seite` | `/neuigkeiten` | URL of the history page |
| `app_name` | empty | Name shown in the dialog title and page title |
| `version` | newest entry | Running version; without it, the topmost numbered changelog entry is used |
| `dialog` | `True` | `False` keeps only the page, without cookie and dialog |
| `cookie_secure` | `False` | Send the cookie over HTTPS only |
| `speicher` | cookie | Custom storage for the last seen version, see [State](#state) |

### Keeping your own layout

Without further setup the page renders in a bundled standalone layout. An
application with its own design instead creates
`templates/web_changelog/layout.html`, which replaces the bundled one:

```jinja
{% extends "base.html" %}
{% block title %}What's new{% endblock %}
{% block content %}{% block wc_inhalt %}{% endblock %}{% endblock %}
```

Base template and block name thus stay in the application, where they belong. A
configuration parameter could not do this, because block names in Jinja cannot
be dynamic.

### Colors

Colors come from custom properties. An application binds them to its design in
a few lines:

```css
.wc-root {
  --wc-akzent: var(--t-accent);
  --wc-flaeche: var(--t-surface-white);
  --wc-text: var(--t-text);
  --wc-rand: var(--t-border);
  --wc-dialog-breite: 760px;
}
```

The library defaults sit in `:where(.wc-root)` and therefore have zero
specificity. A plain `.wc-root` rule of the application always wins, even when
`wc_head()` comes after its stylesheet. All classes are prefixed `wc-` to avoid
collisions.

`--wc-dialog-breite` sets the width of the "What's new" dialog (default 680px).
The dialog always keeps 20px distance from the window edge, so the token never
makes it too wide on small screens.

## Sections

The meaning of a section (`Art`) and its display name are kept apart.
"Verbessert" and "Geändert" are both `Art.GEAENDERT`: same color, same position
in the dialog, different word. An application can thus write in the language of
its users without losing the mapping.

| Vocabulary | Sections | Strictness |
|---|---|---|
| `VOKABULAR_KAC` | Hinzugefügt, Geändert, Veraltet, Entfernt, Behoben, Sicherheit | tolerant |
| `VOKABULAR_ANWENDER` | Neu, Verbessert, Behoben | strict |

A custom vocabulary, for example with English labels:

```python
from web_changelog import Art, Vokabular

ENGLISH = Vokabular(labels={
    Art.NEU: "Added",
    Art.GEAENDERT: "Changed",
    Art.VERALTET: "Deprecated",
    Art.ENTFERNT: "Removed",
    Art.BEHOBEN: "Fixed",
    Art.SICHERHEIT: "Security",
    Art.SONSTIGES: "Other",
})
```

`erlaubte_arten` restricts the allowed sections, `streng=True` additionally
requires the exact spelling of the label.

The parser is always tolerant and never raises; a format error must not break
the running application. Only `pruefe()` is strict, meant as a test in the
pipeline:

```python
from pathlib import Path
from web_changelog import VOKABULAR_ANWENDER, pruefe_datei

problems = pruefe_datei(Path("CHANGELOG.md"), VOKABULAR_ANWENDER)
assert not problems, problems
```

## Changelog fragments and freezing

Open entries live as fragments in `changelog.d/`, one file per change, instead
of being written into the `[Unreleased]` block. Parallel branches then never
touch the same line, so merge conflicts in the changelog cannot occur.

A fragment is named `<section>.<slug>.md`, for example
`behoben.42-duplicate-entries.md`, and contains plain prose. The section prefixes
are `hinzugefuegt`, `geaendert`, `veraltet`, `entfernt`, `behoben` and
`sicherheit`; English headings such as `added` or `fixed` are recognized as
well. Details are in [`changelog.d/README.md`](changelog.d/README.md).

On a version bump, `freeze-changelog` collects the fragments and writes the
dated version block:

```bash
freeze-changelog 1.2.0 --vokabular anwender
```

The package installs `freeze-changelog` as a console script. The repository
also ships `bin/freeze-changelog`, a thin wrapper with the same interface for
projects that call the script by path:

```bash
bin/freeze-changelog <version> [<date>]
```

| Option | Effect |
|---|---|
| `--changelog`, `--fragments` | Paths other than `CHANGELOG.md` and `changelog.d` |
| `--vokabular` | `kac` (default) or `anwender` |
| `--ergaenzen` | Merges into an existing block for the target version instead of skipping the call |
| `--dry-run` | Shows the block that would be written, but writes nothing and deletes no fragments |

Without `--ergaenzen` an existing block stays untouched, so the call can be
repeated safely. With the option, fragments merged during a running bump are
added; date and spelling of the block stay as they are.

A fragment may contain several paragraphs. `freeze` indents the following
paragraphs, the parser keeps them with the same bullet point, and the page shows
them as separate paragraphs. Non-indented prose inside a section, however,
cannot be assigned to any bullet point: it does not appear on the page, and
`pruefe()` reports it. The same applies to a preamble above the first section.

## State

The last seen version is stored in a dedicated cookie (`wc_gesehen`, one year,
`HttpOnly`, `SameSite=Lax`). It deliberately does not use the Flask session,
because not every application has a `SECRET_KEY`, and in some applications the
session is tied to server-side data. Applications with user accounts can plug in
their own storage through the `Speicher` protocol (two methods: `lies()` and
`merke(version)`).

Four rules, taken over from the Swift original:

1. The first visit shows nothing but remembers the version. Otherwise every new
   visitor would get the complete history.
2. A version older than the remembered one shows nothing but remembers the older
   one. A later update then shows the skipped versions again.
3. Only what lies between the remembered and the running version is shown. A
   block for a version not yet released stays out.
4. The version is always remembered, even when nothing is shown.

The cookie is only set on `GET` requests answered with status 200 and
`text/html`, so redirects and health checks do not swallow the release notes.
Every response carrying the dialog or setting the cookie gets `Vary: Cookie`.

## Testing helpers

`web_changelog.testing` provides a throwaway Flask application for tests, used
by the library's own unit and acceptance tests and usable by applications that
want to test their integration:

```python
import shutil
from web_changelog.testing import baue_anwendung

app, root = baue_anwendung()
try:
    client = app.test_client()
    client.get("/")              # first visit: remembers the version, no dialog
    ...
finally:
    shutil.rmtree(root)
```

`baue_anwendung()` accepts `eigenes_layout`, `vokabular`, `dialog` and
`changelog` (the changelog text). The module also exports the sample changelog
`CHANGELOG` used by the fixtures.

## Running the tests

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e . behave
python -m unittest discover -v tests/
python -m behave
```

## License

MIT, see [LICENSE](LICENSE). The name is not covered by the license.
