"""Format-Gate: derselbe Text besteht je nach Vokabular oder faellt durch."""

import unittest

from pathlib import Path

from web_changelog.parser import parse_text
from web_changelog.pruefung import pruefe, pruefe_datei
from web_changelog.vokabular import VOKABULAR_ANWENDER, VOKABULAR_KAC

SAUBER_ANWENDER = """## [0.4.0] — 2026-06-16

### Neu

- Etwas Neues.

### Behoben

- Ein Fehler weniger.
"""


class SauberTest(unittest.TestCase):
    def test_ohne_beanstandung(self):
        self.assertEqual(pruefe(parse_text(SAUBER_ANWENDER), VOKABULAR_ANWENDER), [])

    def test_unreleased_ist_kein_mangel(self):
        # Der leere Block zwischen zwei Releases ist der Normalzustand.
        text = "## [Unreleased]\n\n" + SAUBER_ANWENDER
        self.assertEqual(pruefe(parse_text(text), VOKABULAR_ANWENDER), [])


class VokabularAbhaengigTest(unittest.TestCase):
    """Derselbe Text, zwei Urteile -- die Strenge steckt im Vokabular."""

    TEXT = "## [1.0.0] - 2026-01-01\n\n### Hinzugefügt\n\n- Etwas.\n"

    def test_kac_akzeptiert(self):
        self.assertEqual(pruefe(parse_text(self.TEXT), VOKABULAR_KAC), [])

    def test_anwender_bemaengelt_die_schreibweise(self):
        probleme = pruefe(parse_text(self.TEXT), VOKABULAR_ANWENDER)
        self.assertEqual(len(probleme), 1)
        self.assertIn("Neu", probleme[0])

    def test_anwender_bemaengelt_nicht_erlaubte_art(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Sicherheit\n\n- Etwas.\n"
        self.assertEqual(pruefe(parse_text(text), VOKABULAR_KAC), [])
        probleme = pruefe(parse_text(text), VOKABULAR_ANWENDER)
        self.assertTrue(any("Sicherheit" in p for p in probleme))


class VerwaisterTextTest(unittest.TestCase):
    """Text, der beim Laden verlorenginge, muss auffallen.

    Vorher meldete die Pruefung nichts, und der Verlust fiel erst auf der
    fertigen Seite auf -- beim Release 1.1.0 von digitale-rendite gar nicht.
    """

    def test_prosa_neben_einem_punkt_wird_gemeldet(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Punkt.\n\nVergessene Prosa.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_KAC)
        self.assertEqual(len(probleme), 1)
        self.assertIn("Vergessene Prosa.", probleme[0])
        self.assertIn("nicht angezeigt", probleme[0])

    def test_vorspann_vor_der_ersten_rubrik_wird_gemeldet(self):
        text = "## [1.0.0] - 2026-01-01\n\nWichtige Vorbemerkung.\n\n### Neu\n\n- Etwas.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_KAC)
        self.assertEqual(len(probleme), 1)
        self.assertIn("Wichtige Vorbemerkung.", probleme[0])

    def test_eingerueckter_folgeabsatz_ist_kein_mangel(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Punkt.\n\n  Und ein Absatz.\n"
        self.assertEqual(pruefe(parse_text(text), VOKABULAR_KAC), [])

    def test_langer_text_wird_gekuerzt_zitiert(self):
        lang = "Ein sehr langer Satz, der in der Meldung nicht vollstaendig stehen soll."
        text = f"## [1.0.0] - 2026-01-01\n\n### Neu\n\n- Ein Punkt.\n\n{lang}\n"
        probleme = pruefe(parse_text(text), VOKABULAR_KAC)
        self.assertIn("…", probleme[0])
        self.assertNotIn("stehen soll.", probleme[0])


class MaengelTest(unittest.TestCase):
    def test_leeres_changelog(self):
        probleme = pruefe(parse_text(""), VOKABULAR_ANWENDER)
        self.assertEqual(len(probleme), 1)
        self.assertIn("Keine Versionseintraege", probleme[0])

    def test_nur_unreleased_zaehlt_als_leer(self):
        probleme = pruefe(parse_text("## [Unreleased]\n"), VOKABULAR_ANWENDER)
        self.assertIn("Keine Versionseintraege", probleme[0])

    def test_version_ohne_rubrik(self):
        probleme = pruefe(parse_text("## [1.0.0] - 2026-01-01\n"), VOKABULAR_ANWENDER)
        self.assertTrue(any("keine Rubrik" in p for p in probleme))

    def test_rubrik_ohne_punkte(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Neu\n\n### Behoben\n\n- Etwas.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_ANWENDER)
        self.assertTrue(any("keine Punkte" in p for p in probleme))

    def test_unbekannte_rubrik(self):
        text = "## [1.0.0] - 2026-01-01\n\n### Wunderbares\n\n- Etwas.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_ANWENDER)
        self.assertTrue(any("Wunderbares" in p for p in probleme))

    def test_fehlendes_datum(self):
        text = "## [1.0.0]\n\n### Neu\n\n- Etwas.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_ANWENDER)
        self.assertTrue(any("kein Datum" in p for p in probleme))

    def test_meldungen_nennen_die_version(self):
        text = "## [2.5.1] - 2026-01-01\n\n### Wunderbares\n\n- Etwas.\n"
        probleme = pruefe(parse_text(text), VOKABULAR_ANWENDER)
        self.assertTrue(all("2.5.1" in p for p in probleme))


class EigenesChangelogTest(unittest.TestCase):
    """Das mitgelieferte Changelog haelt sich an seine eigenen Regeln."""

    def test_besteht_das_gate(self):
        pfad = Path(__file__).resolve().parent.parent / "CHANGELOG.md"
        self.assertEqual(pruefe_datei(pfad, VOKABULAR_KAC), [])


if __name__ == "__main__":
    unittest.main()
