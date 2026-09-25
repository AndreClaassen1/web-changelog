"""Versionsnummern: lesen und vergleichen."""

import unittest

from web_changelog.version import Versionsnummer


class ParseTest(unittest.TestCase):
    def test_vollstaendig(self):
        self.assertEqual(Versionsnummer.parse("1.2.3"), Versionsnummer(1, 2, 3))

    def test_fuehrendes_v(self):
        self.assertEqual(Versionsnummer.parse("v1.2"), Versionsnummer(1, 2, 0))
        self.assertEqual(Versionsnummer.parse("V0.4.1"), Versionsnummer(0, 4, 1))

    def test_fehlende_stellen_sind_null(self):
        self.assertEqual(Versionsnummer.parse("1"), Versionsnummer(1, 0, 0))

    def test_vierter_teil_wird_ignoriert(self):
        # Build-Zaehler haengen eine vierte Stelle an. Gruppiert wird aber nach
        # Marketing-Version, sonst zerfaellt der Verlauf in Build-Schnipsel.
        self.assertEqual(Versionsnummer.parse("2.3.4.567"), Versionsnummer(2, 3, 4))

    def test_umgebende_leerzeichen(self):
        self.assertEqual(Versionsnummer.parse("  1.0.0 "), Versionsnummer(1, 0, 0))

    def test_keine_nummer_ist_none(self):
        for roh in ["Unreleased", "", None, "abc", "1.2.3-rc1", "..", "12345678"]:
            with self.subTest(roh=roh):
                self.assertIsNone(Versionsnummer.parse(roh))


class VergleichTest(unittest.TestCase):
    def test_zahlenvergleich_statt_zeichenkette(self):
        # Der Kern: als Zeichenkette waere "0.10.0" < "0.9.0" und der Dialog
        # liesse nach einem groesseren Sprung genau die neuen Eintraege aus.
        self.assertLess(Versionsnummer.parse("0.9.0"), Versionsnummer.parse("0.10.0"))
        self.assertLess(Versionsnummer.parse("0.4.9"), Versionsnummer.parse("0.4.10"))
        self.assertLess(Versionsnummer.parse("1.9.9"), Versionsnummer.parse("2.0.0"))

    def test_gleichheit(self):
        self.assertEqual(Versionsnummer.parse("1.2"), Versionsnummer.parse("1.2.0"))

    def test_sortierung(self):
        roh = ["0.10.0", "0.2.0", "1.0.0", "0.9.9"]
        sortiert = sorted(Versionsnummer.parse(r) for r in roh)
        self.assertEqual([str(v) for v in sortiert], ["0.2.0", "0.9.9", "0.10.0", "1.0.0"])

    def test_str(self):
        self.assertEqual(str(Versionsnummer.parse("v2.1")), "2.1.0")


if __name__ == "__main__":
    unittest.main()
