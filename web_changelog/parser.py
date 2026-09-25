"""Liest eine CHANGELOG.md im Keep-a-Changelog-Format.

Ein schlanker Zeilenscanner ohne Markdown-Abhaengigkeit. Er ist bewusst
**tolerant**: er wirft nie, kennt keine verbotene Rubrik und ueberliest, was er
nicht versteht. Ein Formatfehler soll die laufende Anwendung nicht zerlegen,
sondern ueber ``pruefung.pruefe()`` die Pipeline rot machen.
"""

from __future__ import annotations

import re

from pathlib import Path

from .model import Changelog, Rubrik, Version
from .version import Versionsnummer
from .vokabular import art_aus_ueberschrift

# "## [0.4.0] — 2026-06-16", "## [Unreleased]", "## 1.0.0 - 2026-01-01"
_VERSION_ZEILE = re.compile(r"^##\s+(?P<rest>[^#].*?)\s*$")
# "### Neu"
_RUBRIK_ZEILE = re.compile(r"^###\s+(?P<rubrik>[^#].*?)\s*$")
# "- Eintrag" oder "* Eintrag", auch eingerueckt
_PUNKT_ZEILE = re.compile(r"^\s*[-*]\s+(?P<text>.+?)\s*$")
# Datum am Zeilenende, Trennzeichen tolerant (Geviert, Halbgeviert, Bindestrich)
_DATUM_AM_ENDE = re.compile(r"\s*[—–-]\s*(?P<datum>\d{4}-\d{2}-\d{2})\s*$")
# "[0.4.1]: https://..." — Link-Referenzen am Dateiende, keine Fortsetzung
_LINK_REFERENZ = re.compile(r"^\s*\[[^\]]+\]:\s")


def _kopf_zerlegen(rest: str) -> tuple[str, str | None]:
    """Zerlegt den Rest einer ``##``-Zeile in (Versionstext, Datum oder None)."""
    datum = None
    if (treffer := _DATUM_AM_ENDE.search(rest)):
        datum = treffer.group("datum")
        rest = rest[: treffer.start()]
    return rest.strip().strip("[]").strip(), datum


def parse_text(markdown: str) -> Changelog:
    """Parst den Inhalt einer Changelog-Datei."""
    versionen: list[Version] = []
    version: Version | None = None
    rubrik: Rubrik | None = None
    # Index des zuletzt begonnenen Punktes, an den Fortsetzungszeilen gehen.
    offener_punkt: int | None = None
    # Steht eine Leerzeile zwischen dem offenen Punkt und der naechsten Zeile?
    absatzpause = False

    for zeile in markdown.splitlines():
        if (treffer := _VERSION_ZEILE.match(zeile)):
            text, datum = _kopf_zerlegen(treffer.group("rest"))
            version = Version(version=text, nummer=Versionsnummer.parse(text), datum_iso=datum)
            versionen.append(version)
            rubrik, offener_punkt, absatzpause = None, None, False

        elif version is not None and (treffer := _RUBRIK_ZEILE.match(zeile)):
            ueberschrift = treffer.group("rubrik")
            rubrik = Rubrik(ueberschrift=ueberschrift, art=art_aus_ueberschrift(ueberschrift))
            version.rubriken.append(rubrik)
            offener_punkt, absatzpause = None, False

        elif rubrik is None:
            # Prosa zwischen Versionskopf und erster Rubrik. ``freeze`` schreibt
            # hier den Vorspann hin, angezeigt wird er nicht -- also melden.
            if version is not None and zeile.strip() and not _LINK_REFERENZ.match(zeile):
                version.verwaist.append(zeile.strip())

        elif (treffer := _PUNKT_ZEILE.match(zeile)):
            rubrik.punkte.append(treffer.group("text"))
            offener_punkt, absatzpause = len(rubrik.punkte) - 1, False

        elif not zeile.strip():
            # Eine Leerzeile beendet den Punkt noch nicht: erst die naechste
            # Zeile entscheidet, ob ein eingerueckter Folgeabsatz kommt.
            absatzpause = True

        elif _LINK_REFERENZ.match(zeile):
            offener_punkt, absatzpause = None, False

        elif offener_punkt is None or (absatzpause and zeile[:1] not in (" ", "\t")):
            # Prosa, die zu keinem Punkt gehoert: ohne Punkt davor, oder nach
            # einer Leerzeile ohne Einzug. Sie taucht in der Anzeige nicht auf,
            # ``pruefung.pruefe()`` meldet sie.
            rubrik.verwaist.append(zeile.strip())
            offener_punkt, absatzpause = None, False

        else:
            # Fortsetzung des offenen Punktes: nach einer Leerzeile als eigener
            # Absatz, sonst als umbrochene Zeile desselben Satzes.
            rubrik.punkte[offener_punkt] += ("\n\n" if absatzpause else " ") + zeile.strip()
            absatzpause = False

    return Changelog(versionen=versionen)


def lade(pfad: Path) -> Changelog:
    """Liest und parst eine Changelog-Datei.

    Eine fehlende oder unlesbare Datei ergibt ein leeres Changelog statt eines
    Fehlers: eine Anwendung soll auch dann starten, wenn ihr Changelog beim
    Paketieren vergessen wurde.
    """
    try:
        return parse_text(Path(pfad).read_text(encoding="utf-8"))
    except OSError:
        return Changelog()
