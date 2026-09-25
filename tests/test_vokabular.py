"""Rubriken: Semantik erkennen, Wortwahl der Anwendung respektieren."""

import unittest

from web_changelog.vokabular import (
    KANONISCHE_REIHENFOLGE,
    VOKABULAR_ANWENDER,
    VOKABULAR_KAC,
    Art,
    art_aus_ueberschrift,
)


class ZuordnungTest(unittest.TestCase):
    def test_deutsch(self):
        faelle = {
            "Hinzugefügt": Art.NEU,
            "Neu": Art.NEU,
            "Geändert": Art.GEAENDERT,
            "Verbessert": Art.GEAENDERT,
            "Veraltet": Art.VERALTET,
            "Entfernt": Art.ENTFERNT,
            "Behoben": Art.BEHOBEN,
            "Sicherheit": Art.SICHERHEIT,
        }
        for ueberschrift, art in faelle.items():
            with self.subTest(ueberschrift=ueberschrift):
                self.assertEqual(art_aus_ueberschrift(ueberschrift), art)

    def test_englisch(self):
        faelle = {
            "Added": Art.NEU,
            "Changed": Art.GEAENDERT,
            "Improved": Art.GEAENDERT,
            "Deprecated": Art.VERALTET,
            "Removed": Art.ENTFERNT,
            "Fixed": Art.BEHOBEN,
            "Security": Art.SICHERHEIT,
        }
        for ueberschrift, art in faelle.items():
            with self.subTest(ueberschrift=ueberschrift):
                self.assertEqual(art_aus_ueberschrift(ueberschrift), art)

    def test_umlautfreie_schreibweise(self):
        # Dateinamen in changelog.d erzwingen sie.
        self.assertEqual(art_aus_ueberschrift("hinzugefuegt"), Art.NEU)
        self.assertEqual(art_aus_ueberschrift("geaendert"), Art.GEAENDERT)

    def test_gross_klein_und_leerzeichen(self):
        self.assertEqual(art_aus_ueberschrift("  BEHOBEN  "), Art.BEHOBEN)

    def test_unbekanntes_ist_sonstiges(self):
        self.assertEqual(art_aus_ueberschrift("Wunderbares"), Art.SONSTIGES)


class LabelTest(unittest.TestCase):
    def test_dieselbe_art_zwei_woerter(self):
        # Der Kern der Trennung: gleiche Semantik, andere Beschriftung.
        self.assertEqual(VOKABULAR_KAC.label(Art.GEAENDERT), "Geändert")
        self.assertEqual(VOKABULAR_ANWENDER.label(Art.GEAENDERT), "Verbessert")

    def test_sonstiges_behaelt_die_rohe_ueberschrift(self):
        self.assertEqual(VOKABULAR_KAC.label(Art.SONSTIGES, roh="Wunderbares"), "Wunderbares")

    def test_sonstiges_ohne_rohtext(self):
        self.assertEqual(VOKABULAR_KAC.label(Art.SONSTIGES), "Sonstiges")


class CssTest(unittest.TestCase):
    """Die CSS-Klasse haengt an der Art (``wc-badge-<art.value>``).

    Damit tragen "Verbessert" und "Geändert" dieselbe Klasse, und keine
    Anwendung braucht wegen ihrer Wortwahl eigenes CSS.
    """

    def test_suffix_ist_umlautfrei_und_stabil(self):
        for art in KANONISCHE_REIHENFOLGE:
            with self.subTest(art=art):
                self.assertTrue(art.value.isascii(), f"{art} liefert kein ASCII")
                self.assertEqual(art.value, art.value.lower())

    def test_suffix_haengt_nicht_am_label(self):
        self.assertNotEqual(
            VOKABULAR_ANWENDER.label(Art.GEAENDERT),
            VOKABULAR_KAC.label(Art.GEAENDERT),
        )
        self.assertEqual(Art.GEAENDERT.value, "geaendert")


class StrengeTest(unittest.TestCase):
    def test_kac_erlaubt_alles(self):
        self.assertTrue(all(VOKABULAR_KAC.erlaubt(a) for a in KANONISCHE_REIHENFOLGE))
        self.assertFalse(VOKABULAR_KAC.streng)

    def test_anwender_erlaubt_drei(self):
        self.assertTrue(VOKABULAR_ANWENDER.erlaubt(Art.NEU))
        self.assertTrue(VOKABULAR_ANWENDER.erlaubt(Art.GEAENDERT))
        self.assertTrue(VOKABULAR_ANWENDER.erlaubt(Art.BEHOBEN))
        self.assertFalse(VOKABULAR_ANWENDER.erlaubt(Art.SICHERHEIT))
        self.assertFalse(VOKABULAR_ANWENDER.erlaubt(Art.VERALTET))


class SlugTest(unittest.TestCase):
    def test_kac_slugs(self):
        self.assertEqual(VOKABULAR_KAC.art_fuer_slug("hinzugefuegt"), Art.NEU)
        self.assertEqual(VOKABULAR_KAC.art_fuer_slug("sicherheit"), Art.SICHERHEIT)

    def test_anwender_slugs(self):
        self.assertEqual(VOKABULAR_ANWENDER.art_fuer_slug("verbessert"), Art.GEAENDERT)

    def test_anwender_akzeptiert_hausstandard_als_alias(self):
        # Ein aus Muskelgedaechtnis benanntes Fragment soll einsortiert werden
        # statt liegen zu bleiben.
        self.assertEqual(VOKABULAR_ANWENDER.art_fuer_slug("hinzugefuegt"), Art.NEU)
        self.assertEqual(VOKABULAR_ANWENDER.art_fuer_slug("geaendert"), Art.GEAENDERT)

    def test_unbekannter_slug(self):
        self.assertIsNone(VOKABULAR_ANWENDER.art_fuer_slug("quatsch"))


class ReihenfolgeTest(unittest.TestCase):
    def test_kac_volle_reihenfolge(self):
        self.assertEqual(VOKABULAR_KAC.reihenfolge(), KANONISCHE_REIHENFOLGE)

    def test_anwender_eingeschraenkt(self):
        self.assertEqual(
            VOKABULAR_ANWENDER.reihenfolge(),
            (Art.NEU, Art.GEAENDERT, Art.BEHOBEN, Art.SONSTIGES),
        )

    def test_sonstiges_bleibt_hinten_moeglich(self):
        # Damit beim Einfrieren nichts verlorengeht.
        self.assertIn(Art.SONSTIGES, VOKABULAR_ANWENDER.reihenfolge())


if __name__ == "__main__":
    unittest.main()
