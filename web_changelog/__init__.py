"""Changelog-Seite und Was-ist-neu-Dialog fuer Flask-Anwendungen.

Portierung des Swift-Pakets AppChangelog. Kurzform der Einbindung:

    from web_changelog import Changelogs, VOKABULAR_ANWENDER

    Changelogs(app, pfad=..., vokabular=VOKABULAR_ANWENDER)

Im Layout der Anwendung ``{{ wc_head() }}`` in den Kopf und ``{{ wc_whatsnew() }}``
vor das Ende des Rumpfes setzen.

``Changelogs`` wird erst bei Zugriff nachgeladen. Das haelt den Import fuer die
Nutzung ohne Web-Kontext schlank -- das Freeze-Skript und ein Format-Gate in der
CI brauchen weder Flask noch Jinja, obwohl beides als Abhaengigkeit vorhanden
ist.
"""

from .model import Changelog, Rubrik, Version
from .parser import lade, parse_text
from .pruefung import pruefe, pruefe_datei
from .version import Versionsnummer
from .vokabular import (
    KANONISCHE_REIHENFOLGE,
    VOKABULAR_ANWENDER,
    VOKABULAR_KAC,
    Art,
    Vokabular,
    art_aus_ueberschrift,
)
from .whatsnew import Faellig, Speicher, hole_faellige

__all__ = [
    "Art",
    "Changelog",
    "Changelogs",
    "Faellig",
    "KANONISCHE_REIHENFOLGE",
    "Rubrik",
    "Speicher",
    "VOKABULAR_ANWENDER",
    "VOKABULAR_KAC",
    "Version",
    "Versionsnummer",
    "Vokabular",
    "art_aus_ueberschrift",
    "hole_faellige",
    "lade",
    "parse_text",
    "pruefe",
    "pruefe_datei",
]


def __getattr__(name: str):
    """``Changelogs`` erst bei Bedarf laden, damit Flask nicht mitimportiert wird."""
    if name == "Changelogs":
        from .blueprint import Changelogs

        return Changelogs
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
