"""Parser: Struktur lesen, tolerant bleiben."""

import tempfile
import unittest

from pathlib import Path

from web_changelog.parser import lade, parse_text
from web_changelog.testing import ABSATZ_ERSTER, ABSATZ_ZWEITER
from web_changelog.vokabular import Art

BEISPIEL = """# Änderungshistorie

Eine Einleitung, die kein Versionseintrag ist.

## [Unreleased]

## [0.4.0] — 2026-06-16

### Neu

- Erster Punkt.
- Zweiter Punkt.

### Behoben

- Ein Fehler weniger.

## [0.3.0] – 2026-06-15

### Verbessert

- Schneller geworden.

[0.4.0]: https://example.invalid/0.4.0
"""


class StrukturTest(unittest.TestCase):
    def setUp(self):
        self.changelog = parse_text(BEISPIEL)

    def test_reihenfolge_bleibt_wie_in_der_datei(self):
        self.assertEqual(
            [v.version for v in self.changelog.versionen],
            ["Unreleased", "0.4.0", "0.3.0"],
        )

    def test_unreleased_hat_keine_nummer(self):
        self.assertIsNone(self.changelog.versionen[0].nummer)

    def test_veroeffentlichte_lassen_unreleased_aus(self):
        # Unreleased hat keine Nummer und keinen Inhalt, gehoert also nicht in
        # die Anzeige.
        self.assertEqual([v.version for v in self.changelog.veroeffentlichte], ["0.4.0", "0.3.0"])

    def test_rubriken_und_punkte(self):
        v = self.changelog.veroeffentlichte[0]
        self.assertEqual([r.ueberschrift for r in v.rubriken], ["Neu", "Behoben"])
        self.assertEqual(v.rubriken[0].punkte, ["Erster Punkt.", "Zweiter Punkt."])

    def test_art_wird_zugeordnet(self):
        v = self.changelog.veroeffentlichte[1]
        self.assertEqual(v.rubriken[0].art, Art.GEAENDERT)  # "Verbessert"

    def test_datum_deutsch(self):
        self.assertEqual(self.changelog.veroeffentlichte[0].datum_de, "16. Juni 2026")

    def test_trennzeichen_tolerant(self):
        # Geviert- und Halbgeviertstrich kommen beide vor.
        self.assertEqual(self.changelog.veroeffentlichte[1].datum_iso, "2026-06-15")

    def test_link_referenz_ist_kein_punkt(self):
        letzte = self.changelog.veroeffentlichte[1]
        self.assertEqual(letzte.rubriken[0].punkte, ["Schneller geworden."])

    def test_neueste_nummer(self):
        self.assertEqual(str(self.changelog.neueste_nummer), "0.4.0")


class FortsetzungszeilenTest(unittest.TestCase):
    """Umbrochene Punkte muessen zusammenbleiben, sonst enden Saetze mittendrin."""

    def test_eingerueckte_fortsetzung(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Satz, der\n  umbrochen wurde.\n"
        punkte = parse_text(text).veroeffentlichte[0].rubriken[0].punkte
        self.assertEqual(punkte, ["Ein Satz, der umbrochen wurde."])

    def test_nicht_eingerueckte_fortsetzung(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Satz, der\nauch so umbrochen wurde.\n"
        punkte = parse_text(text).veroeffentlichte[0].rubriken[0].punkte
        self.assertEqual(punkte, ["Ein Satz, der auch so umbrochen wurde."])

    def test_leerzeile_schliesst_den_punkt(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Punkt.\n\nLose Prosa.\n"
        punkte = parse_text(text).veroeffentlichte[0].rubriken[0].punkte
        self.assertEqual(punkte, ["Ein Punkt."])

    def test_mehrere_punkte_bleiben_getrennt(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Eins\n  weiter.\n- Zwei\n"
        punkte = parse_text(text).veroeffentlichte[0].rubriken[0].punkte
        self.assertEqual(punkte, ["Eins weiter.", "Zwei"])


class FolgeabsaetzeTest(unittest.TestCase):
    """Ein Fragment mit mehreren Absaetzen muss vollstaendig ankommen.

    Beim Release 1.1.0 von digitale-rendite verlor ein solcher Eintrag
    Entwurfskennzeichnung, Risikoabschnitt und Eurobetraege, weil die Leerzeile
    den Punkt schloss.
    """

    TEXT = (
        "## [1.1.0] - 2026-09-11\n\n### Neu\n\n"
        f"- {ABSATZ_ERSTER}\n"
        "\n"
        f"  {ABSATZ_ZWEITER}\n"
        "\n"
        "  Die Vorlage geht danach in die Fraktionen.\n"
    )

    def setUp(self):
        self.rubrik = parse_text(self.TEXT).veroeffentlichte[0].rubriken[0]

    def test_absaetze_bleiben_ein_punkt(self):
        self.assertEqual(len(self.rubrik.punkte), 1)

    def test_kein_absatz_geht_verloren(self):
        self.assertIn(ABSATZ_ZWEITER, self.rubrik.punkte[0])
        self.assertIn("Fraktionen", self.rubrik.punkte[0])

    def test_absaetze_sind_getrennt_abrufbar(self):
        self.assertEqual(len(self.rubrik.absaetze[0]), 3)

    def test_nichts_bleibt_verwaist(self):
        self.assertEqual(self.rubrik.verwaist, [])

    def test_umbruch_bleibt_ein_absatz(self):
        # Ein Zeilenumbruch ohne Leerzeile ist kein neuer Absatz.
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Satz, der\n  umbrochen wurde.\n"
        rubrik = parse_text(text).veroeffentlichte[0].rubriken[0]
        self.assertEqual(rubrik.absaetze, [["Ein Satz, der umbrochen wurde."]])

    def test_naechster_punkt_beendet_den_absatz(self):
        text = (
            "## [1.0.0] - 2026-01-01\n\n### Neu\n\n"
            "- Eins.\n\n  Noch dazu.\n\n- Zwei.\n"
        )
        rubrik = parse_text(text).veroeffentlichte[0].rubriken[0]
        self.assertEqual(rubrik.punkte, ["Eins.\n\nNoch dazu.", "Zwei."])


class VerwaisteProsaTest(unittest.TestCase):
    """Was sich nicht einem Punkt zuordnen laesst, wird erfasst statt verworfen."""

    def test_nicht_eingerueckte_prosa_nach_einem_punkt(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Punkt.\n\nLose Prosa.\n"
        rubrik = parse_text(text).veroeffentlichte[0].rubriken[0]
        self.assertEqual(rubrik.punkte, ["Ein Punkt."])
        self.assertEqual(rubrik.verwaist, ["Lose Prosa."])

    def test_prosa_ohne_punkt_davor(self):
        # Ohne Punkte gilt die Version als leer, taucht also gar nicht erst in
        # der Anzeige auf. Die Pruefung findet sie ueber ``versionen`` trotzdem.
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\nNur Prosa.\n"
        rubrik = parse_text(text).versionen[0].rubriken[0]
        self.assertEqual(rubrik.punkte, [])
        self.assertEqual(rubrik.verwaist, ["Nur Prosa."])

    def test_vorspann_vor_der_ersten_rubrik(self):
        # ``freeze`` schreibt einen Vorspann direkt unter den Versionskopf.
        # Angezeigt wird er nicht, verschwiegen werden darf er trotzdem nicht.
        text = "## [1.0.0] - 2026-01-01\n\nWichtige Vorbemerkung.\n\n### Neu\n\n- Etwas.\n"
        version = parse_text(text).veroeffentlichte[0]
        self.assertEqual(version.verwaist, ["Wichtige Vorbemerkung."])
        self.assertEqual(version.rubriken[0].punkte, ["Etwas."])

    def test_einleitung_vor_der_ersten_version_zaehlt_nicht(self):
        # Der Text ueber dem ersten Versionskopf gehoert zur Datei, nicht zu
        # einer Version.
        changelog = parse_text(BEISPIEL)
        self.assertTrue(all(not v.verwaist for v in changelog.versionen))

    def test_link_referenz_ist_nicht_verwaist(self):
        rubrik = parse_text(BEISPIEL).veroeffentlichte[1].rubriken[0]
        self.assertEqual(rubrik.verwaist, [])


class ToleranzTest(unittest.TestCase):
    """Der Parser wirft nie -- ein Formatfehler darf die Anwendung nicht zerlegen."""

    def test_unbekannte_rubrik_wird_sonstiges(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Wunderbares\n\n- Etwas.\n"
        rubrik = parse_text(text).veroeffentlichte[0].rubriken[0]
        self.assertEqual(rubrik.art, Art.SONSTIGES)
        self.assertEqual(rubrik.ueberschrift, "Wunderbares")

    def test_englische_rubriken(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Added\n\n- Something.\n\n### Fixed\n\n- A bug.\n"
        arten = [r.art for r in parse_text(text).veroeffentlichte[0].rubriken]
        self.assertEqual(arten, [Art.NEU, Art.BEHOBEN])

    def test_ohne_klammern_und_ohne_datum(self):
        changelog = parse_text("## 1.0.0\n\n### Neu\n\n- Etwas.\n")
        version = changelog.veroeffentlichte[0]
        self.assertEqual(str(version.nummer), "1.0.0")
        self.assertEqual(version.datum_de, "")

    def test_rubrik_ohne_version_wird_ignoriert(self):
        self.assertEqual(parse_text("### Neu\n\n- Etwas.\n").versionen, [])

    def test_leerer_text(self):
        self.assertEqual(parse_text("").versionen, [])

    def test_sternchen_als_aufzaehlung(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n* Mit Sternchen.\n"
        self.assertEqual(parse_text(text).veroeffentlichte[0].rubriken[0].punkte, ["Mit Sternchen."])


class LadenTest(unittest.TestCase):
    def test_datei(self):
        with tempfile.NamedTemporaryFile("w", suffix=".md", encoding="utf-8", delete=False) as f:
            f.write(BEISPIEL)
            pfad = Path(f.name)
        try:
            self.assertEqual(len(lade(pfad).veroeffentlichte), 2)
        finally:
            pfad.unlink()

    def test_fehlende_datei_ist_leer(self):
        # Eine Anwendung soll auch dann starten, wenn ihr Changelog beim
        # Paketieren vergessen wurde.
        changelog = lade(Path("/gibt/es/nicht/CHANGELOG.md"))
        self.assertEqual(changelog.versionen, [])
        self.assertIsNone(changelog.neueste_nummer)


class EigenesChangelogTest(unittest.TestCase):
    """Das mitgelieferte Changelog muss selbst lesbar sein."""

    def test_parsebar(self):
        pfad = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
        changelog = lade(pfad)
        self.assertTrue(changelog.veroeffentlichte)
        for version in changelog.veroeffentlichte:
            self.assertTrue(version.rubriken, f"Version {version.version} ohne Rubrik")


if __name__ == "__main__":
    unittest.main()
