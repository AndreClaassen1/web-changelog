"""Was ist neu seit dem letzten Besuch.

Portierung von ``WhatsNewState.consumePending`` aus AppChangelog. Die Reihenfolge
der Schritte in ``hole_faellige()`` ist bindend -- siehe dort.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from .model import Changelog, Rubrik, Version
from .version import Versionsnummer
from .vokabular import Art, Vokabular


@runtime_checkable
class Speicher(Protocol):
    """Ablage der zuletzt gesehenen Version.

    Mit Absicht winzig: eine Anwendung mit Nutzerkonten kann die Version am
    Profil speichern, ohne dass die Regel unten davon etwas mitbekommt.
    """

    def lies(self) -> str | None:
        ...

    def merke(self, version: str) -> None:
        ...


@dataclass(frozen=True)
class Faellig:
    """Was dem Besucher gezeigt werden soll."""

    vorher: Versionsnummer
    versionen: list[Version]

    @property
    def neueste(self) -> Version:
        return self.versionen[0]

    def zusammengefasst(self, vokabular: Vokabular) -> list[Rubrik]:
        """Verschmilzt die Rubriken aller faelligen Versionen zu einer Liste.

        Ohne Versionskoepfe und in kanonischer Reihenfolge -- das ist der
        Unterschied zwischen dem Dialog und der Verlaufsseite. Wer zwei Updates
        uebersprungen hat, soll eine lesbare Liste sehen und nicht dreimal
        dieselbe Rubrik.
        """
        gesammelt: dict[Art, list[str]] = {}
        ueberschriften: dict[Art, str] = {}
        for version in self.versionen:
            for rubrik in version.rubriken:
                gesammelt.setdefault(rubrik.art, []).extend(rubrik.punkte)
                ueberschriften.setdefault(rubrik.art, rubrik.ueberschrift)

        return [
            Rubrik(ueberschrift=ueberschriften[art], art=art, punkte=gesammelt[art])
            for art in vokabular.sortiere(gesammelt)
            if gesammelt[art]
        ]


def hole_faellige(
    speicher: Speicher,
    aktuell: Versionsnummer,
    changelog: Callable[[], Changelog],
) -> Faellig | None:
    """Ermittelt die faelligen Neuerungen UND merkt sich die laufende Version.

    Beides in einem Schritt, weil das Auseinanderziehen fehlertraechtig ist: wer
    zuerst entscheidet und erst danach merkt, zeigt bei jedem Aufruf erneut
    denselben Dialog, sobald ein Zweig das Merken ueberspringt.

    Die Reihenfolge ist bindend:

    1. Gleiche Version wie gemerkt: nichts tun, insbesondere nicht schreiben.
    2. **Merken -- immer**, auch wenn gleich nichts angezeigt wird.
    3. Erstbesuch (nichts gemerkt) und Rueckschritt auf eine aeltere Version:
       still bleiben. Sonst bekaeme jeder Neuzugang den kompletten Verlauf.
    4. Faellig ist, was echt neuer als die gemerkte und hoechstens so neu wie die
       laufende Version ist. Die Obergrenze verhindert, dass ein Block zu einer
       noch nicht ausgelieferten Version vorab erscheint.

    ``changelog`` ist ein Callable (Pendant zum ``@autoclosure`` im Original):
    ohne Versionssprung wird die Datei gar nicht erst angefasst.
    """
    vorher = Versionsnummer.parse(speicher.lies())

    if vorher == aktuell:
        return None

    speicher.merke(str(aktuell))

    if vorher is None or not vorher < aktuell:
        return None

    faellig = changelog().bereich(nach=vorher, bis=aktuell)
    return Faellig(vorher=vorher, versionen=faellig) if faellig else None
