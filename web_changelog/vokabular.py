"""Rubriken: was sie bedeuten, und wie eine Anwendung sie nennt.

Zwei Ebenen, bewusst getrennt:

* **Art** ist die Semantik. Sie bestimmt Farbe, CSS-Klasse, Reihenfolge und die
  Zusammenfassung im Dialog.
* **Anzeigename** ist die Wortwahl der Anwendung und kommt aus dem ``Vokabular``.

Damit ist der Konflikt geloest, dass die eine Anwendung "Verbessert" schreibt und
die andere "Geaendert": beides ist ``Art.GEAENDERT`` und wird gleich behandelt,
nur eben anders beschriftet.

Portierung von ``ChangelogSectionKind(heading:)`` aus AppChangelog, inklusive der
Erkennung englischer Ueberschriften.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType
from typing import Iterable, Mapping


class Art(str, Enum):
    """Semantische Rubrik. Der Wert ist zugleich der CSS-Suffix (umlautfrei)."""

    NEU = "neu"
    GEAENDERT = "geaendert"
    VERALTET = "veraltet"
    ENTFERNT = "entfernt"
    BEHOBEN = "behoben"
    SICHERHEIT = "sicherheit"
    SONSTIGES = "sonstiges"


#: Reihenfolge, in der Rubriken angezeigt und im Dialog zusammengefasst werden.
#: SONSTIGES steht hinten, damit Unbekanntes nicht verschwindet, aber auch nicht
#: das Wichtige verdraengt.
KANONISCHE_REIHENFOLGE: tuple[Art, ...] = (
    Art.NEU,
    Art.GEAENDERT,
    Art.VERALTET,
    Art.ENTFERNT,
    Art.BEHOBEN,
    Art.SICHERHEIT,
    Art.SONSTIGES,
)

# Ueberschrift (klein, ohne Rand) -> Art. Deutsch und englisch, weil Changelogs
# aus verschiedenen Quellen zusammenkommen. Umlautlose Schreibweisen sind
# ebenfalls erfasst, weil Dateinamen sie erzwingen.
_UEBERSCHRIFT_ZU_ART: Mapping[str, Art] = MappingProxyType({
    "added": Art.NEU,
    "hinzugefügt": Art.NEU,
    "hinzugefuegt": Art.NEU,
    "neu": Art.NEU,
    "changed": Art.GEAENDERT,
    "geändert": Art.GEAENDERT,
    "geaendert": Art.GEAENDERT,
    "improved": Art.GEAENDERT,
    "verbessert": Art.GEAENDERT,
    "deprecated": Art.VERALTET,
    "veraltet": Art.VERALTET,
    "removed": Art.ENTFERNT,
    "entfernt": Art.ENTFERNT,
    "fixed": Art.BEHOBEN,
    "fixes": Art.BEHOBEN,
    "bugfixes": Art.BEHOBEN,
    "behoben": Art.BEHOBEN,
    "security": Art.SICHERHEIT,
    "sicherheit": Art.SICHERHEIT,
})


def art_aus_ueberschrift(ueberschrift: str) -> Art:
    """Ordnet eine Rubrik-Ueberschrift ihrer Art zu.

    Unbekanntes wird ``Art.SONSTIGES`` statt eines Fehlers -- die Anzeige behaelt
    dann die rohe Ueberschrift bei, damit nichts unterschlagen wird.
    """
    return _UEBERSCHRIFT_ZU_ART.get(ueberschrift.strip().lower(), Art.SONSTIGES)


@dataclass(frozen=True)
class Vokabular:
    """Wortwahl und Strenge einer Anwendung.

    :param labels: Anzeigename je Art.
    :param erlaubte_arten: Wenn gesetzt, bemaengelt ``pruefe()`` jede andere Art.
    :param streng: Wenn wahr, muss die Schreibweise exakt dem Label entsprechen.
    """

    labels: Mapping[Art, str]
    erlaubte_arten: frozenset[Art] | None = None
    streng: bool = False

    def label(self, art: Art, roh: str = "") -> str:
        """Anzeigename der Art; bei SONSTIGES die rohe Ueberschrift."""
        if art is Art.SONSTIGES:
            return roh.strip() or self.labels.get(art, "Sonstiges")
        return self.labels.get(art, art.value.capitalize())

    def erlaubt(self, art: Art) -> bool:
        return self.erlaubte_arten is None or art in self.erlaubte_arten

    def art_fuer_slug(self, slug: str) -> Art | None:
        """Art zu einem Dateinamen-Praefix aus ``changelog.d``, oder None.

        Nutzt dieselbe Tabelle wie die Ueberschriften-Erkennung, statt eine
        zweite zu pflegen: ein Slug ist nichts anderes als eine umlautfrei
        geschriebene Rubrik. Damit sind fuer ein Anwender-Vokabular auch die
        Hausstandard-Namen (``hinzugefuegt``, ``geaendert``) gueltig und landen
        unter der richtigen Art, statt als unbekannt liegen zu bleiben.
        """
        art = art_aus_ueberschrift(slug)
        return art if art is not Art.SONSTIGES and self.erlaubt(art) else None

    def slugs(self) -> tuple[str, ...]:
        """Beispiel-Dateinamen fuer Fehlermeldungen: je erlaubter Art einer."""
        return tuple(
            self.label(art).lower().replace("ä", "ae").replace("ö", "oe")
            .replace("ü", "ue").replace("ß", "ss")
            for art in self.reihenfolge()
            if art is not Art.SONSTIGES
        )

    def reihenfolge(self) -> tuple[Art, ...]:
        """Kanonische Reihenfolge, auf die erlaubten Arten eingeschraenkt."""
        if self.erlaubte_arten is None:
            return KANONISCHE_REIHENFOLGE
        erlaubt = tuple(a for a in KANONISCHE_REIHENFOLGE if a in self.erlaubte_arten)
        # SONSTIGES bleibt immer hinten moeglich, damit unbekannte Rubriken beim
        # Einfrieren nicht verlorengehen -- bemaengelt werden sie trotzdem.
        return erlaubt if Art.SONSTIGES in erlaubt else erlaubt + (Art.SONSTIGES,)

    def sortiere(self, arten: Iterable[Art]) -> list[Art]:
        """Bringt vorhandene Arten in die kanonische Reihenfolge.

        Arten ausserhalb der Reihenfolge haengen hinten an, statt zu
        verschwinden: weder die Anzeige noch ein Release soll etwas
        unterschlagen, das jemand hineingeschrieben hat.
        """
        vorhanden = list(arten)
        bekannte = [a for a in self.reihenfolge() if a in vorhanden]
        return bekannte + [a for a in vorhanden if a not in bekannte]


_LABELS_KAC = MappingProxyType({
    Art.NEU: "Hinzugefügt",
    Art.GEAENDERT: "Geändert",
    Art.VERALTET: "Veraltet",
    Art.ENTFERNT: "Entfernt",
    Art.BEHOBEN: "Behoben",
    Art.SICHERHEIT: "Sicherheit",
    Art.SONSTIGES: "Sonstiges",
})

#: Keep a Changelog, sechs Rubriken, tolerant. Der Hausstandard.
VOKABULAR_KAC = Vokabular(labels=_LABELS_KAC)

#: Drei Rubriken in Anwendersprache, streng. Fuer Anwendungen, deren Changelog
#: Endnutzer lesen (Kommunen, Fachbereiche) statt Entwickler.
VOKABULAR_ANWENDER = Vokabular(
    labels=MappingProxyType({**_LABELS_KAC, Art.NEU: "Neu", Art.GEAENDERT: "Verbessert"}),
    erlaubte_arten=frozenset({Art.NEU, Art.GEAENDERT, Art.BEHOBEN}),
    streng=True,
)
