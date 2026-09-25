"""Versionsnummern nach Semantic Versioning, vergleichbar und tolerant beim Lesen.

Portierung von ``SemanticVersion`` aus dem Swift-Paket AppChangelog. Toleriert
wird alles, was in Changelogs und Build-Systemen ueblich vorkommt: ein
fuehrendes ``v``, fehlende Stellen (``1.2`` ist ``1.2.0``) und ein vierter Teil,
wie ihn Build-Zaehler anhaengen. Der vierte Teil wird bewusst IGNORIERT --
gruppiert wird ausschliesslich nach Marketing-Version.
"""

from __future__ import annotations

import re

from dataclasses import dataclass

# "0.4.1", "v1.2", "1", "2.3.4.567" (vierter Teil wird verworfen)
_MUSTER = re.compile(r"^\s*[vV]?(\d{1,6})(?:\.(\d{1,6}))?(?:\.(\d{1,6}))?(?:\.\d{1,6})?\s*$")


@dataclass(frozen=True, order=True)
class Versionsnummer:
    """Eine Versionsnummer, verglichen nach Zahlenwert statt nach Zeichenkette.

    Der Zeichenkettenvergleich, den Vorgaengerloesungen benutzt haben, ordnet
    ``"0.10.0"`` vor ``"0.9.0"`` ein und laesst damit genau die Eintraege aus,
    die nach einem groesseren Sprung anstehen.
    """

    major: int
    minor: int = 0
    patch: int = 0

    @classmethod
    def parse(cls, roh: str | None) -> Versionsnummer | None:
        """Liest eine Versionsnummer, oder None wenn die Eingabe keine ist.

        ``None`` ist der Normalfall fuer ``[Unreleased]`` und fuer ein fehlendes
        oder manipuliertes Cookie -- kein Fehler, sondern "keine Angabe".
        """
        if not roh:
            return None
        treffer = _MUSTER.match(roh)
        if treffer is None:
            return None
        major, minor, patch = (int(t) if t is not None else 0 for t in treffer.groups())
        return cls(major=major, minor=minor, patch=patch)

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"
