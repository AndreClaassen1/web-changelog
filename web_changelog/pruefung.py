"""Format-Gate: prueft ein Changelog gegen das Vokabular einer Anwendung.

Der einzige Ort mit Strenge. Der Parser laesst alles durch, damit die laufende
Anwendung nicht an einem Tippfehler zerbricht; hier faellt derselbe Tippfehler
dafuer im Test auf, bevor er ausgeliefert wird.
"""

from __future__ import annotations

import textwrap

from pathlib import Path

from .model import Changelog
from .parser import lade
from .vokabular import Vokabular


def pruefe(changelog: Changelog, vokabular: Vokabular) -> list[str]:
    """Liefert eine Liste von Problemen; leer bedeutet in Ordnung.

    Geprueft werden nur nummerierte Versionen. Ein leerer ``[Unreleased]``-Block
    ist der Normalzustand zwischen zwei Releases und kein Mangel.
    """
    probleme: list[str] = []
    nummeriert = [v for v in changelog.versionen if v.nummer is not None]

    if not nummeriert:
        return ["Keine Versionseintraege gefunden (Format '## [x.y.z] - JJJJ-MM-TT'?)."]

    for version in nummeriert:
        for text in version.verwaist:
            probleme.append(_verlust(f"Version {version.version}", text))
        if not version.rubriken:
            erlaubt = _erlaubte_labels(vokabular)
            probleme.append(f"Version {version.version}: keine Rubrik ({erlaubt}).")
        if not version.datum_iso:
            probleme.append(f"Version {version.version}: kein Datum im Format JJJJ-MM-TT.")

        for rubrik in version.rubriken:
            if not vokabular.erlaubt(rubrik.art):
                erlaubt = _erlaubte_labels(vokabular)
                probleme.append(
                    f"Version {version.version}: unbekannte Rubrik "
                    f"'{rubrik.ueberschrift}' (erlaubt: {erlaubt})."
                )
            elif vokabular.streng and rubrik.ueberschrift != vokabular.label(rubrik.art):
                erwartet = vokabular.label(rubrik.art)
                probleme.append(
                    f"Version {version.version}: Rubrik '{rubrik.ueberschrift}' "
                    f"muss '{erwartet}' heissen."
                )
            if not rubrik.punkte:
                probleme.append(
                    f"Version {version.version}, Rubrik '{rubrik.ueberschrift}': keine Punkte."
                )
            for text in rubrik.verwaist:
                probleme.append(
                    _verlust(f"Version {version.version}, Rubrik '{rubrik.ueberschrift}'", text)
                )

    return probleme


def pruefe_datei(pfad: Path, vokabular: Vokabular) -> list[str]:
    """Wie ``pruefe()``, liest die Datei aber selbst ein."""
    return pruefe(lade(pfad), vokabular)


def _erlaubte_labels(vokabular: Vokabular) -> str:
    if vokabular.erlaubte_arten is None:
        return "beliebig"
    return ", ".join(
        vokabular.label(art)
        for art in vokabular.reihenfolge()
        if art in vokabular.erlaubte_arten
    )


def _verlust(wo: str, text: str) -> str:
    """Meldung fuer Text, der beim Anzeigen unter den Tisch fiele.

    Genau so gingen beim Release 1.1.0 von digitale-rendite Folgeabsaetze
    verloren, ohne dass es jemandem auffiel.
    """
    zitat = textwrap.shorten(text, width=60, placeholder="…")
    return (
        f"{wo}: Text ausserhalb eines Punktes wird nicht angezeigt ('{zitat}'). "
        f"Als '- '-Punkt schreiben oder um zwei Leerzeichen einruecken, damit er "
        f"zum Punkt davor gehoert."
    )
