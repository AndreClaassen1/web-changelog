"""Einfrieren offener Eintraege.

Der wichtigste Teil ist die Rueckwaertskompatibilitaet: fuer VOKABULAR_KAC muss
dasselbe herauskommen wie beim frueheren Skript, das in mehreren Repos als Kopie
liegt. Sonst driften diese Repos beim naechsten Release auseinander.
"""

import contextlib
import io
import shutil
import tempfile
import unittest

from pathlib import Path

from web_changelog.freeze import (
    als_aufzaehlung,
    block_text,
    freeze,
    lies_fragmente,
    main,
    trenner_aus_datei,
)
from web_changelog.parser import parse_text
from web_changelog.pruefung import pruefe
from web_changelog.testing import ABSATZ_ERSTER, ABSATZ_ZWEITER
from web_changelog.vokabular import VOKABULAR_ANWENDER, VOKABULAR_KAC, Art

VORHER = """# Änderungshistorie

## [Unreleased]

## [0.1.0] – 2026-01-01

### Hinzugefügt

- Der Anfang.
"""


class KacKompatibilitaetTest(unittest.TestCase):
    """Erwartete Ausgabe, wortgetreu wie beim frueheren bin/freeze-changelog."""

    def test_block_aufbau(self):
        fragmente = {Art.NEU: ["- Etwas Neues."], Art.BEHOBEN: ["- Ein Fehler weniger."]}
        neu, meldung = freeze(VORHER, "0.2.0", "2026-02-01", fragmente, VOKABULAR_KAC)

        erwartet = """# Änderungshistorie

## [Unreleased]

## [0.2.0] – 2026-02-01

### Hinzugefügt

- Etwas Neues.

### Behoben

- Ein Fehler weniger.

## [0.1.0] – 2026-01-01

### Hinzugefügt

- Der Anfang.
"""
        self.assertEqual(neu, erwartet)
        self.assertIn("eingefroren als 0.2.0", meldung)

    def test_kanonische_reihenfolge_unabhaengig_von_der_eingabe(self):
        fragmente = {Art.SICHERHEIT: ["- S."], Art.NEU: ["- N."], Art.BEHOBEN: ["- B."]}
        neu, _ = freeze(VORHER, "0.2.0", "2026-02-01", fragmente, VOKABULAR_KAC)
        self.assertLess(neu.index("### Hinzugefügt"), neu.index("### Behoben"))
        self.assertLess(neu.index("### Behoben"), neu.index("### Sicherheit"))

    def test_bestehende_unreleased_eintraege_werden_zusammengefuehrt(self):
        text = VORHER.replace(
            "## [Unreleased]\n", "## [Unreleased]\n\n### Behoben\n\n- Von Hand notiert.\n"
        )
        neu, _ = freeze(text, "0.2.0", "2026-02-01", {Art.BEHOBEN: ["- Aus Fragment."]}, VOKABULAR_KAC)
        self.assertIn("- Von Hand notiert.\n- Aus Fragment.", neu)


class NichtstunTest(unittest.TestCase):
    def test_ohne_eintraege_kein_leerer_block(self):
        # Ein Infrastruktur-Release ohne sichtbare Aenderung bekommt keinen Block.
        neu, meldung = freeze(VORHER, "0.2.0", "2026-02-01", {}, VOKABULAR_KAC)
        self.assertEqual(neu, VORHER)
        self.assertIn("Keine offenen Eintraege", meldung)

    def test_vorhandener_block_bleibt_unangetastet(self):
        # Der Aufruf muss wiederholbar sein, etwa nach einem CI-Neustart.
        neu, meldung = freeze(VORHER, "0.1.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC)
        self.assertEqual(neu, VORHER)
        self.assertIn("existiert bereits", meldung)
        self.assertIn("--ergaenzen", meldung)

    def test_ohne_unreleased_block(self):
        text = "# Titel\n\n## [0.1.0] – 2026-01-01\n\n### Hinzugefügt\n\n- Der Anfang.\n"
        neu, meldung = freeze(text, "0.2.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC)
        self.assertEqual(neu, text)
        self.assertIn("Kein [Unreleased]-Block", meldung)


class ErgaenzenTest(unittest.TestCase):
    """Nachtrag in einen bestehenden Block.

    Werden waehrend eines Bumps weitere Branches mit Fragmenten gemergt, gibt es
    den Block zur Zielversion schon. Ohne diese Option bleiben die Fragmente
    liegen und muessen von Hand eingetragen werden.
    """

    def test_fragment_landet_im_bestehenden_block(self):
        neu, meldung = freeze(
            VORHER, "0.1.0", "2026-02-01", {Art.NEU: ["- Spaeter dazu."]},
            VOKABULAR_KAC, ergaenze=True,
        )
        self.assertIn("- Der Anfang.\n- Spaeter dazu.", neu)
        self.assertIn("um 1 Eintrag ergaenzt", meldung)

    def test_meldung_zaehlt_punkte_nicht_bloecke(self):
        # Ein Fragment kann mehrere Punkte tragen; die Meldung soll nicht
        # weniger nennen, als hinzukommt.
        _, meldung = freeze(
            VORHER, "0.1.0", "2026-02-01", {Art.NEU: ["- Eins.\n- Zwei.\n- Drei."]},
            VOKABULAR_KAC, ergaenze=True,
        )
        self.assertIn("um 3 Eintraege ergaenzt", meldung)

    def test_kopf_des_bestehenden_blocks_bleibt(self):
        # Datum und Schreibweise sind bewusst gesetzt und duerfen sich durch
        # einen Nachtrag nicht verschieben.
        neu, _ = freeze(
            VORHER, "0.1.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC, ergaenze=True
        )
        self.assertIn("## [0.1.0] – 2026-01-01", neu)
        self.assertNotIn("2026-02-01", neu)

    def test_neue_rubrik_wird_einsortiert(self):
        neu, _ = freeze(
            VORHER, "0.1.0", "2026-02-01", {Art.BEHOBEN: ["- Ein Fehler weniger."]},
            VOKABULAR_KAC, ergaenze=True,
        )
        self.assertLess(neu.index("### Hinzugefügt"), neu.index("### Behoben"))

    def test_offene_unreleased_eintraege_wandern_mit(self):
        text = VORHER.replace(
            "## [Unreleased]\n", "## [Unreleased]\n\n### Behoben\n\n- Von Hand notiert.\n"
        )
        neu, _ = freeze(text, "0.1.0", "2026-02-01", {}, VOKABULAR_KAC, ergaenze=True)
        self.assertIn("- Von Hand notiert.", neu)
        # Der Unreleased-Block bleibt leer zurueck, damit nichts doppelt steht.
        kopf, _, rest = neu.partition("## [Unreleased]")
        self.assertTrue(rest.lstrip().startswith("## [0.1.0]"), rest[:60])

    def test_ohne_offene_eintraege_passiert_nichts(self):
        neu, meldung = freeze(VORHER, "0.1.0", "2026-02-01", {}, VOKABULAR_KAC, ergaenze=True)
        self.assertEqual(neu, VORHER)
        self.assertIn("Keine offenen Eintraege", meldung)

    def test_ohne_vorhandenen_block_wird_normal_eingefroren(self):
        # Die Option soll den Regelfall nicht veraendern.
        mit, _ = freeze(
            VORHER, "0.2.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC, ergaenze=True
        )
        ohne, _ = freeze(VORHER, "0.2.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC)
        self.assertEqual(mit, ohne)

    def test_ergebnis_bleibt_parsebar(self):
        neu, _ = freeze(
            VORHER, "0.1.0", "2026-02-01", {Art.BEHOBEN: ["- Ein Fehler weniger."]},
            VOKABULAR_KAC, ergaenze=True,
        )
        geparst = parse_text(neu)
        version = geparst.veroeffentlichte[0]
        self.assertEqual(version.version, "0.1.0")
        self.assertEqual([r.punkte for r in version.rubriken],
                         [["Der Anfang."], ["Ein Fehler weniger."]])
        self.assertEqual(pruefe(geparst, VOKABULAR_KAC), [])


class TrennzeichenTest(unittest.TestCase):
    def test_uebernimmt_das_zeichen_der_datei(self):
        # Sonst mischt eine Datei mit Geviertstrich ab dem ersten Einfrieren
        # zwei Schreibweisen.
        geviert = VORHER.replace("–", "—")
        neu, _ = freeze(geviert, "0.2.0", "2026-02-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC)
        self.assertIn("## [0.2.0] — 2026-02-01", neu)
        self.assertNotIn("## [0.2.0] – ", neu)

    def test_fallback_ohne_vorhandenen_kopf(self):
        text = "# Titel\n\n## [Unreleased]\n"
        self.assertEqual(trenner_aus_datei(text), "–")
        neu, _ = freeze(text, "0.1.0", "2026-01-01", {Art.NEU: ["- X."]}, VOKABULAR_KAC)
        self.assertIn("## [0.1.0] – 2026-01-01", neu)


class AnwenderVokabularTest(unittest.TestCase):
    def test_labels_der_anwendung(self):
        fragmente = {Art.NEU: ["- N."], Art.GEAENDERT: ["- V."], Art.BEHOBEN: ["- B."]}
        neu, _ = freeze(VORHER, "0.2.0", "2026-02-01", fragmente, VOKABULAR_ANWENDER)
        self.assertIn("### Neu", neu)
        self.assertIn("### Verbessert", neu)
        self.assertNotIn("### Geändert", neu)


class FragmenteTest(unittest.TestCase):
    def _schreibe(self, verzeichnis, dateien):
        for name, inhalt in dateien.items():
            (verzeichnis / name).write_text(inhalt, encoding="utf-8")

    def test_einsammeln_nach_art(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._schreibe(d, {
                "hinzugefuegt.1-a.md": "Erstes.",
                "behoben.2-b.md": "Zweites.",
            })
            eintraege, dateien, warnungen = lies_fragmente(d, VOKABULAR_KAC)
            self.assertEqual(eintraege[Art.NEU], ["- Erstes."])
            self.assertEqual(eintraege[Art.BEHOBEN], ["- Zweites."])
            self.assertEqual(len(dateien), 2)
            self.assertEqual(warnungen, [])

    def test_readme_wird_uebergangen(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._schreibe(d, {"README.md": "Erklaertext", "neu.1-a.md": "Etwas."})
            eintraege, dateien, warnungen = lies_fragmente(d, VOKABULAR_ANWENDER)
            self.assertEqual(len(dateien), 1)
            self.assertEqual(warnungen, [])

    def test_unbekannter_slug_bleibt_liegen(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._schreibe(d, {"quatsch.1-a.md": "Etwas."})
            eintraege, dateien, warnungen = lies_fragmente(d, VOKABULAR_KAC)
            self.assertEqual(eintraege, {})
            self.assertEqual(dateien, [])
            self.assertTrue(warnungen)

    def test_anwender_akzeptiert_hausstandard_slug(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._schreibe(d, {"hinzugefuegt.1-a.md": "Etwas."})
            eintraege, _, warnungen = lies_fragmente(d, VOKABULAR_ANWENDER)
            self.assertEqual(eintraege[Art.NEU], ["- Etwas."])
            self.assertEqual(warnungen, [])

    def test_leeres_fragment_bleibt_liegen(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            self._schreibe(d, {"behoben.1-a.md": "   \n"})
            eintraege, dateien, warnungen = lies_fragmente(d, VOKABULAR_KAC)
            self.assertEqual(dateien, [])
            self.assertTrue(warnungen)

    def test_fehlendes_verzeichnis(self):
        eintraege, dateien, warnungen = lies_fragmente(Path("/gibt/es/nicht"), VOKABULAR_KAC)
        self.assertEqual((eintraege, dateien, warnungen), ({}, [], []))


class AufzaehlungTest(unittest.TestCase):
    def test_prosa_wird_ein_punkt(self):
        self.assertEqual(als_aufzaehlung("Ein Satz."), "- Ein Satz.")

    def test_mehrzeilige_prosa_wird_eingerueckt(self):
        self.assertEqual(als_aufzaehlung("Erste\nzweite"), "- Erste\n  zweite")

    def test_eigene_punkte_bleiben_unangetastet(self):
        self.assertEqual(als_aufzaehlung("- Eins\n- Zwei"), "- Eins\n- Zwei")

    def test_leer(self):
        self.assertEqual(als_aufzaehlung("  \n "), "")


class AblageMixin:
    """Legt Changelog und Fragmente in einem Wegwerf-Verzeichnis an."""

    def ablage(self, **fragmente: str) -> tuple[Path, Path]:
        """Liefert (Pfad zum Changelog, Pfad zum Fragment-Verzeichnis).

        Die Schluesselwoerter sind Dateinamen ohne Endung, die Werte der Inhalt;
        Unterstriche werden zu Punkten, weil ein Dateiname wie
        ``behoben.1-a.md`` kein gueltiger Bezeichner ist.
        """
        wurzel = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, wurzel, ignore_errors=True)
        changelog = wurzel / "CHANGELOG.md"
        changelog.write_text(VORHER, encoding="utf-8")
        verzeichnis = wurzel / "changelog.d"
        verzeichnis.mkdir()
        for name, inhalt in fragmente.items():
            (verzeichnis / f"{name.replace('_', '.')}.md").write_text(inhalt, encoding="utf-8")
        return changelog, verzeichnis


class CliTest(AblageMixin, unittest.TestCase):
    """Ruft ``main`` mit stummgeschaltetem stdout -- die Fortschrittsmeldungen
    gehoeren ins CI-Log, nicht in die Testausgabe."""

    @staticmethod
    def _stumm(argv):
        with contextlib.redirect_stdout(io.StringIO()):
            return main(argv)

    def test_schreibt_und_loescht_fragmente(self):
        changelog, fragmente = self.ablage(behoben_1_a="Ein Fehler weniger.")

        code = self._stumm(["0.2.0", "2026-02-01",
                            "--changelog", str(changelog), "--fragments", str(fragmente)])

        self.assertEqual(code, 0)
        self.assertIn("## [0.2.0] – 2026-02-01", changelog.read_text(encoding="utf-8"))
        self.assertEqual(list(fragmente.glob("*.md")), [],
                         "uebernommenes Fragment muss geloescht sein")

    def test_dry_run_schreibt_nichts(self):
        changelog, fragmente = self.ablage(behoben_1_a="Ein Fehler weniger.")

        with contextlib.redirect_stdout(io.StringIO()) as ausgabe:
            code = main(["0.2.0", "2026-02-01", "--dry-run",
                         "--changelog", str(changelog), "--fragments", str(fragmente)])

        self.assertEqual(code, 0)
        self.assertEqual(changelog.read_text(encoding="utf-8"), VORHER)
        self.assertEqual(len(list(fragmente.glob("*.md"))), 1,
                         "Probelauf darf kein Fragment loeschen")
        text = ausgabe.getvalue()
        self.assertIn("Probelauf", text)
        self.assertIn("## [0.2.0] – 2026-02-01", text)
        self.assertIn("- Ein Fehler weniger.", text)

    def test_ergaenzen_ueber_die_kommandozeile(self):
        changelog, fragmente = self.ablage(hinzugefuegt_2_b="Spaeter dazu.")

        code = self._stumm(["0.1.0", "--ergaenzen",
                            "--changelog", str(changelog), "--fragments", str(fragmente)])

        self.assertEqual(code, 0)
        self.assertIn("- Spaeter dazu.", changelog.read_text(encoding="utf-8"))

    def test_fehlende_datei_ist_kein_fehler(self):
        # Ein uebersprungener Einfrier-Schritt darf den Release nicht aufhalten.
        self.assertEqual(self._stumm(["1.0.0", "--changelog", "/gibt/es/nicht.md"]), 0)


class MehrabsaetzigesFragmentTest(AblageMixin, unittest.TestCase):
    """Rundlauf: Fragment mit Absaetzen, einfrieren, wieder lesen.

    Genau hier ging beim Release 1.1.0 von digitale-rendite Text verloren: das
    Fragment wurde korrekt eingerueckt geschrieben, der Parser las aber nur den
    ersten Absatz, und die Pruefung meldete nichts.
    """

    def test_alle_absaetze_kommen_auf_der_seite_an(self):
        changelog, fragmente = self.ablage(
            neu_82_ratsvorlage=f"{ABSATZ_ERSTER}\n\n{ABSATZ_ZWEITER}\n"
        )

        with contextlib.redirect_stdout(io.StringIO()):
            main(["0.2.0", "2026-02-01", "--vokabular", "anwender",
                  "--changelog", str(changelog), "--fragments", str(fragmente)])

        # Nur der neue Block, denn der alte traegt die KaC-Schreibweise.
        geparst = parse_text(block_text(changelog.read_text(encoding="utf-8"), "0.2.0"))
        rubrik = geparst.veroeffentlichte[0].rubriken[0]
        self.assertEqual(len(rubrik.punkte), 1)
        self.assertEqual(rubrik.absaetze[0], [ABSATZ_ERSTER, ABSATZ_ZWEITER])
        self.assertEqual(pruefe(geparst, VOKABULAR_ANWENDER), [])


class BlockTextTest(unittest.TestCase):
    def test_liefert_kopf_und_rumpf(self):
        self.assertEqual(
            block_text(VORHER, "0.1.0"),
            "## [0.1.0] – 2026-01-01\n\n### Hinzugefügt\n\n- Der Anfang.\n",
        )

    def test_unbekannte_version_ist_leer(self):
        self.assertEqual(block_text(VORHER, "9.9.9"), "")


if __name__ == "__main__":
    unittest.main()
