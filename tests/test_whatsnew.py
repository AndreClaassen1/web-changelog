"""Die Kernregel: was wird nach einem Update gezeigt, und was wird gemerkt.

Portierung von ``WhatsNewStateTests`` aus AppChangelog. Diese Datei ist der
Grund, warum die Schrittfolge in ``hole_faellige`` nicht umgestellt werden darf.
"""

import unittest

from web_changelog.parser import parse_text
from web_changelog.version import Versionsnummer
from web_changelog.vokabular import VOKABULAR_ANWENDER, Art
from web_changelog.whatsnew import hole_faellige

CHANGELOG = parse_text("""
## [0.5.0] - 2026-07-31

### Neu

- Fuenf-Null-Neuerung.

### Behoben

- Fuenf-Null-Fehler.

## [0.4.0] - 2026-06-16

### Neu

- Vier-Null-Neuerung.

## [0.3.0] - 2026-06-15

### Verbessert

- Drei-Null-Verbesserung.
""")


class SpeicherAttrappe:
    """Minimaler Speicher; zaehlt Schreibvorgaenge mit."""

    def __init__(self, wert=None):
        self.wert = wert
        self.schreibvorgaenge = []

    def lies(self):
        return self.wert

    def merke(self, version):
        self.wert = version
        self.schreibvorgaenge.append(version)


def _changelog_zaehler():
    """Liefert (Callable, Aufrufzaehler) zum Pruefen der Lazy-Regel."""
    aufrufe = []

    def laden():
        aufrufe.append(1)
        return CHANGELOG

    return laden, aufrufe


class ErstbesuchTest(unittest.TestCase):
    def test_zeigt_nichts_merkt_aber(self):
        # Sonst bekaeme jeder Neuzugang den kompletten Verlauf vorgesetzt.
        speicher = SpeicherAttrappe(None)
        self.assertIsNone(hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG))
        self.assertEqual(speicher.wert, "0.5.0")

    def test_changelog_wird_nicht_gelesen(self):
        laden, aufrufe = _changelog_zaehler()
        hole_faellige(SpeicherAttrappe(None), Versionsnummer(0, 5, 0), laden)
        self.assertEqual(aufrufe, [])


class GleicheVersionTest(unittest.TestCase):
    def test_zeigt_nichts(self):
        speicher = SpeicherAttrappe("0.5.0")
        self.assertIsNone(hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG))

    def test_schreibt_nicht_erneut(self):
        # Der Normalfall bei jedem Seitenaufruf: kein Cookie neu setzen.
        speicher = SpeicherAttrappe("0.5.0")
        hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG)
        self.assertEqual(speicher.schreibvorgaenge, [])

    def test_changelog_wird_nicht_gelesen(self):
        laden, aufrufe = _changelog_zaehler()
        hole_faellige(SpeicherAttrappe("0.5.0"), Versionsnummer(0, 5, 0), laden)
        self.assertEqual(aufrufe, [])


class RueckschrittTest(unittest.TestCase):
    def test_zeigt_nichts_merkt_aber_die_aeltere(self):
        # Nach einem Rollback soll ein spaeteres Update die uebersprungenen
        # Versionen erneut zeigen. Dafuer muss die aeltere Nummer gemerkt werden.
        speicher = SpeicherAttrappe("0.5.0")
        self.assertIsNone(hole_faellige(speicher, Versionsnummer(0, 4, 0), lambda: CHANGELOG))
        self.assertEqual(speicher.wert, "0.4.0")


class SprungTest(unittest.TestCase):
    def test_eine_version_weiter(self):
        speicher = SpeicherAttrappe("0.4.0")
        faellig = hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG)
        self.assertIsNotNone(faellig)
        self.assertEqual([v.version for v in faellig.versionen], ["0.5.0"])
        self.assertEqual(str(faellig.vorher), "0.4.0")
        self.assertEqual(speicher.wert, "0.5.0")

    def test_zwei_versionen_uebersprungen(self):
        speicher = SpeicherAttrappe("0.3.0")
        faellig = hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG)
        self.assertEqual([v.version for v in faellig.versionen], ["0.5.0", "0.4.0"])

    def test_gemerkte_version_selbst_ist_nicht_faellig(self):
        speicher = SpeicherAttrappe("0.4.0")
        faellig = hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG)
        self.assertNotIn("0.4.0", [v.version for v in faellig.versionen])

    def test_obergrenze_ist_die_laufende_version(self):
        # Ein Block zu einer noch nicht ausgelieferten Version darf nicht vorab
        # erscheinen.
        speicher = SpeicherAttrappe("0.3.0")
        faellig = hole_faellige(speicher, Versionsnummer(0, 4, 0), lambda: CHANGELOG)
        self.assertEqual([v.version for v in faellig.versionen], ["0.4.0"])

    def test_sprung_ohne_eintraege_dazwischen(self):
        # Version hochgezaehlt, aber kein Changelog-Block dazu: nichts zeigen,
        # trotzdem merken.
        speicher = SpeicherAttrappe("0.5.0")
        self.assertIsNone(hole_faellige(speicher, Versionsnummer(0, 6, 0), lambda: CHANGELOG))
        self.assertEqual(speicher.wert, "0.6.0")

    def test_neueste_ist_die_oberste(self):
        faellig = hole_faellige(SpeicherAttrappe("0.3.0"), Versionsnummer(0, 5, 0), lambda: CHANGELOG)
        self.assertEqual(faellig.neueste.version, "0.5.0")


class ManipuliertesCookieTest(unittest.TestCase):
    def test_unlesbarer_wert_gilt_als_erstbesuch(self):
        speicher = SpeicherAttrappe("kaputt")
        self.assertIsNone(hole_faellige(speicher, Versionsnummer(0, 5, 0), lambda: CHANGELOG))
        self.assertEqual(speicher.wert, "0.5.0")


class ZusammenfassungTest(unittest.TestCase):
    """Der Dialog verschmilzt die Rubriken aller faelligen Versionen."""

    def setUp(self):
        self.faellig = hole_faellige(
            SpeicherAttrappe("0.3.0"), Versionsnummer(0, 5, 0), lambda: CHANGELOG
        )

    def test_keine_doppelten_rubriken(self):
        rubriken = self.faellig.zusammengefasst(VOKABULAR_ANWENDER)
        arten = [r.art for r in rubriken]
        self.assertEqual(len(arten), len(set(arten)))

    def test_punkte_aller_versionen(self):
        rubriken = self.faellig.zusammengefasst(VOKABULAR_ANWENDER)
        neu = next(r for r in rubriken if r.art is Art.NEU)
        self.assertEqual(neu.punkte, ["Fuenf-Null-Neuerung.", "Vier-Null-Neuerung."])

    def test_kanonische_reihenfolge(self):
        # Neu vor Behoben, unabhaengig von der Reihenfolge in der Datei.
        rubriken = self.faellig.zusammengefasst(VOKABULAR_ANWENDER)
        self.assertEqual([r.art for r in rubriken], [Art.NEU, Art.BEHOBEN])

    def test_label_kommt_aus_dem_vokabular(self):
        rubriken = self.faellig.zusammengefasst(VOKABULAR_ANWENDER)
        self.assertEqual(rubriken[0].label(VOKABULAR_ANWENDER), "Neu")


if __name__ == "__main__":
    unittest.main()
