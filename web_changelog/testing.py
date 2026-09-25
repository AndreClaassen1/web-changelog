"""Wegwerf-Anwendung fuer Tests -- an einer Stelle, nicht je Testart neu.

Unit-Tests und Akzeptanztests hatten diesen Aufbau zunaechst getrennt, und die
Changelog-Fixtures liefen prompt auseinander: dieselbe Version trug in der einen
Kopie andere Rubriken als in der anderen. Beide bauen jetzt auf dieser Vorlage
auf.

Auch fuer Anwendungen nutzbar, die die Einbindung bei sich testen wollen.
"""

from __future__ import annotations

import tempfile

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template

from .blueprint import Changelogs
from .vokabular import VOKABULAR_ANWENDER, Vokabular

#: Drei Versionen, damit sich ein uebersprungenes Update pruefen laesst.
CHANGELOG = """# Änderungshistorie

## [Unreleased]

## [0.5.0] — 2026-07-31

### Neu

- Fuenf-Null-Neuerung.

### Behoben

- Fuenf-Null-Fehler.

## [0.4.0] — 2026-06-16

### Neu

- Vier-Null-Neuerung.

## [0.3.0] — 2026-06-15

### Verbessert

- Drei-Null-Verbesserung.
"""

#: Ein Eintrag aus zwei Absaetzen, so eingerueckt, wie ``freeze`` ihn aus einem
#: mehrabsaetzigen Fragment schreibt. Der Regressionsfall aus dem Release 1.1.0
#: von digitale-rendite; hier, damit Unit- und Akzeptanztests denselben Text
#: sehen und nicht auseinanderdriften.
ABSATZ_ERSTER = "Ratsvorlage als Entwurf gekennzeichnet."
ABSATZ_ZWEITER = "Der Risikoabschnitt weist bis zu 250.000 Euro aus."

CHANGELOG_ABSAETZE = CHANGELOG.replace(
    "- Fuenf-Null-Neuerung.",
    f"- {ABSATZ_ERSTER}\n\n  {ABSATZ_ZWEITER}",
)

#: Basis-Template der Testanwendung. Die Marke belegt in Tests, dass das Layout
#: der Anwendung gewonnen hat und nicht das mitgelieferte.
BASIS = """<!DOCTYPE html>
<html><body><header class="marke-der-anwendung">Testanwendung</header>
{% block inhalt %}{% endblock %}
{{ wc_whatsnew() }}
</body></html>
"""

#: Der Layout-Seam: verdraengt web_changelog/layout.html der Bibliothek.
EIGENES_LAYOUT = """{% extends "basis.html" %}
{% block inhalt %}{% block wc_inhalt %}{% endblock %}{% endblock %}
"""


def baue_anwendung(
    eigenes_layout: bool = True,
    vokabular: Vokabular = VOKABULAR_ANWENDER,
    dialog: bool = True,
    changelog: str = CHANGELOG,
) -> tuple[Flask, Path]:
    """Liefert (Anwendung, Wurzelverzeichnis).

    Das Verzeichnis muss der Aufrufer aufraeumen; es haelt Changelog und
    Templates, die zur Laufzeit von der Platte gelesen werden.
    """
    wurzel = Path(tempfile.mkdtemp())
    (wurzel / "CHANGELOG.md").write_text(changelog, encoding="utf-8")

    templates = wurzel / "templates"
    (templates / "web_changelog").mkdir(parents=True)
    (templates / "basis.html").write_text(BASIS, encoding="utf-8")
    if eigenes_layout:
        (templates / "web_changelog" / "layout.html").write_text(EIGENES_LAYOUT, encoding="utf-8")

    # Eindeutiger Importname je Anwendung, sonst teilen sich mehrere
    # Testanwendungen im selben Prozess ihren Jinja-Cache.
    app = Flask(f"wc_test_{wurzel.name}", template_folder=str(templates))
    changelogs = Changelogs(
        app,
        pfad=wurzel / "CHANGELOG.md",
        vokabular=vokabular,
        pfad_seite="/neuigkeiten",
        app_name="Testanwendung",
        dialog=dialog,
    )
    app.extensions["web_changelog"] = changelogs

    @app.route("/")
    def start():
        return render_template("basis.html")

    @app.route("/api/health")
    def health():
        return jsonify(status="ok")

    @app.route("/weiter")
    def weiter():
        return redirect("/")

    return app, wurzel
