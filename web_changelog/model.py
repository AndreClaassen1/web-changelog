"""Datenmodell eines Changelogs: Rubrik, Version, Changelog."""

from __future__ import annotations

from dataclasses import dataclass, field

from .version import Versionsnummer
from .vokabular import Art, Vokabular

_MONATE = (
    "Januar", "Februar", "März", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
)


@dataclass
class Rubrik:
    """Eine Rubrik mit ihren Punkten.

    ``ueberschrift`` ist die Schreibweise aus der Datei, ``art`` die daraus
    abgeleitete Semantik. Beides wird gebraucht: die Art zum Einordnen, die
    Ueberschrift, um bei unbekannten Rubriken nichts zu unterschlagen.

    ``verwaist`` sammelt Prosa, die zu keinem Punkt gehoert und deshalb nicht
    angezeigt werden kann. Sie wird nicht stillschweigend verworfen, sondern von
    ``pruefung.pruefe()`` gemeldet.
    """

    ueberschrift: str
    art: Art
    punkte: list[str] = field(default_factory=list)
    verwaist: list[str] = field(default_factory=list)

    def label(self, vokabular: Vokabular) -> str:
        return vokabular.label(self.art, roh=self.ueberschrift)

    @property
    def absaetze(self) -> list[list[str]]:
        """Je Punkt seine Absaetze; einabsaetzige Punkte ergeben eine Liste mit
        einem Element.

        Mehrabsaetzige Punkte entstehen aus Fragmenten mit Leerzeile: der Parser
        haelt sie zusammen, die Anzeige setzt die Folgeabsaetze als eigene
        Absaetze in denselben Listenpunkt.
        """
        return [punkt.split("\n\n") for punkt in self.punkte]


@dataclass
class Version:
    """Ein Versionseintrag mit Datum und Rubriken.

    ``version`` ist die Zeichenkette aus der Datei (etwa ``"0.4.1"`` oder
    ``"Unreleased"``), ``nummer`` die daraus gelesene Versionsnummer -- ``None``
    bei ``[Unreleased]`` und allem, was sich nicht als Nummer lesen laesst.
    """

    version: str
    nummer: Versionsnummer | None = None
    datum_iso: str | None = None
    rubriken: list[Rubrik] = field(default_factory=list)
    #: Prosa zwischen Versionskopf und erster Rubrik. Wird nicht angezeigt, aber
    #: auch nicht verschwiegen: ``pruefung.pruefe()`` meldet sie.
    verwaist: list[str] = field(default_factory=list)

    @property
    def datum_de(self) -> str:
        """Datum in deutscher Schreibweise, etwa '16. Juni 2026'; sonst leer."""
        if not self.datum_iso:
            return ""
        try:
            jahr, monat, tag = (int(t) for t in self.datum_iso.split("-"))
            return f"{tag}. {_MONATE[monat - 1]} {jahr}"
        except (ValueError, IndexError):
            return self.datum_iso

    @property
    def hat_inhalt(self) -> bool:
        return any(rubrik.punkte for rubrik in self.rubriken)


@dataclass
class Changelog:
    """Alle Versionen einer Datei, in Dateireihenfolge (neueste zuerst)."""

    versionen: list[Version] = field(default_factory=list)

    @property
    def veroeffentlichte(self) -> list[Version]:
        """Versionen mit Nummer und Inhalt.

        Damit fallen ``[Unreleased]`` und leere Bloecke heraus, die beim
        Einfrieren entstehen koennen. Die Anzeige soll nur zeigen, was
        tatsaechlich ausgeliefert wurde.
        """
        return [v for v in self.versionen if v.nummer is not None and v.hat_inhalt]

    @property
    def neueste_nummer(self) -> Versionsnummer | None:
        veroeffentlicht = self.veroeffentlichte
        return veroeffentlicht[0].nummer if veroeffentlicht else None

    def bereich(self, nach: Versionsnummer, bis: Versionsnummer) -> list[Version]:
        """Veroeffentlichte Versionen mit ``nach < nummer <= bis``, neueste zuerst.

        Die Obergrenze verhindert, dass ein Changelog-Block zu einer noch nicht
        ausgelieferten Version vorab erscheint.
        """
        return [v for v in self.veroeffentlichte if nach < v.nummer <= bis]
