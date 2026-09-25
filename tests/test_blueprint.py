"""Flask-Anbindung: Seite, Cookie, Dialog, Layout-Seam."""

import shutil
import unittest

from flask import Flask

from web_changelog import Changelogs
from web_changelog.testing import baue_anwendung


class FlaskFall(unittest.TestCase):
    """Baut je Test eine Wegwerf-Anwendung mit echtem Changelog auf der Platte."""

    eigenes_layout = False
    dialog = True

    def setUp(self):
        self.app, self.wurzel = baue_anwendung(
            eigenes_layout=self.eigenes_layout, dialog=self.dialog
        )
        self.changelogs = self.app.extensions["web_changelog"]
        self.client = self.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.wurzel, ignore_errors=True)

    def client_mit_gesehener_version(self, version):
        """Testclient mit gesetztem Cookie.

        Ueber ``set_cookie`` statt ueber einen ``Cookie``-Header: der Testclient
        von Werkzeug fuellt den Header aus seinem eigenen Speicher und
        ueberschreibt einen von Hand gesetzten wieder.
        """
        client = self.app.test_client()
        client.set_cookie("wc_gesehen", version)
        return client


class SeiteTest(FlaskFall):
    def test_erreichbar(self):
        antwort = self.client.get("/neuigkeiten")
        self.assertEqual(antwort.status_code, 200)

    def test_zeigt_alle_versionen_mit_kopf(self):
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn("v0.5.0", text)
        self.assertIn("v0.4.0", text)

    def test_labels_aus_dem_vokabular(self):
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn(">Verbessert<", text)
        self.assertNotIn(">Geändert<", text)

    def test_css_klasse_haengt_an_der_art(self):
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn("wc-badge-geaendert", text)

    def test_unreleased_erscheint_nicht(self):
        self.assertNotIn("Unreleased", self.client.get("/neuigkeiten").get_data(as_text=True))

    def test_kein_dialog_auf_der_seite_selbst(self):
        # Sonst stuende dasselbe zweimal auf einer Seite.
        antwort = self.client_mit_gesehener_version("0.4.0").get("/neuigkeiten")
        self.assertNotIn("wc-dialog", antwort.get_data(as_text=True))

    def test_seite_merkt_die_version_trotzdem(self):
        antwort = self.client_mit_gesehener_version("0.4.0").get("/neuigkeiten")
        self.assertIn("wc_gesehen=0.5.0", antwort.headers.get("Set-Cookie", ""))


class VersionTest(FlaskFall):
    def test_aus_dem_obersten_eintrag(self):
        self.assertEqual(str(self.changelogs.aktuelle_version), "0.5.0")


class ErstbesuchTest(FlaskFall):
    def test_kein_dialog(self):
        text = self.client.get("/").get_data(as_text=True)
        self.assertNotIn("wc-dialog", text)

    def test_cookie_wird_gesetzt(self):
        antwort = self.client.get("/")
        self.assertIn("wc_gesehen=0.5.0", antwort.headers.get("Set-Cookie", ""))

    def test_cookie_ist_httponly(self):
        antwort = self.client.get("/")
        self.assertIn("HttpOnly", antwort.headers.get("Set-Cookie", ""))


class DialogTest(FlaskFall):
    def test_erscheint_nach_versionssprung(self):
        antwort = self.client_mit_gesehener_version("0.4.0").get("/")
        text = antwort.get_data(as_text=True)
        self.assertIn("wc-dialog", text)
        self.assertIn("Fuenf-Null-Neuerung.", text)

    def test_nennt_die_vorherige_version(self):
        text = self.client_mit_gesehener_version("0.4.0").get("/").get_data(as_text=True)
        self.assertIn("0.4.0", text)

    def test_zeigt_nur_neue_versionen(self):
        text = self.client_mit_gesehener_version("0.4.0").get("/").get_data(as_text=True)
        self.assertNotIn("Vier-Null-Verbesserung.", text)

    def test_erscheint_genau_einmal(self):
        # Der zweite Aufruf traegt das inzwischen gesetzte Cookie.
        erster = self.client_mit_gesehener_version("0.4.0").get("/")
        self.assertIn("wc-dialog", erster.get_data(as_text=True))
        zweiter = self.client.get("/")
        self.assertNotIn("wc-dialog", zweiter.get_data(as_text=True))

    def test_vary_cookie(self):
        # Ohne das liefert ein Proxy die Dialog-Variante an alle aus.
        antwort = self.client_mit_gesehener_version("0.4.0").get("/")
        self.assertIn("Cookie", antwort.headers.get("Vary", ""))

    def test_manipuliertes_cookie_gilt_als_erstbesuch(self):
        antwort = self.client_mit_gesehener_version("<script>").get("/")
        self.assertNotIn("wc-dialog", antwort.get_data(as_text=True))


class CookieNurAufSichtbarenAntwortenTest(FlaskFall):
    """Sonst verbraucht ein Health-Check die Release-Notes unbemerkt."""

    def test_nicht_auf_json(self):
        antwort = self.client.get("/api/health")
        self.assertNotIn("wc_gesehen", antwort.headers.get("Set-Cookie", ""))

    def test_nicht_auf_redirect(self):
        antwort = self.client.get("/weiter")
        self.assertNotIn("wc_gesehen", antwort.headers.get("Set-Cookie", ""))

    def test_dialog_ueberlebt_einen_health_check(self):
        self.client.get("/api/health")
        antwort = self.client_mit_gesehener_version("0.4.0").get("/")
        self.assertIn("wc-dialog", antwort.get_data(as_text=True))


class MitgeliefertesLayoutTest(FlaskFall):
    def test_eigenstaendige_seite(self):
        # Anwendungen ohne eigenes Basis-Template bekommen ohne Konfiguration
        # eine vollstaendige Seite.
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn("<!DOCTYPE html>", text)
        self.assertIn("wc-standalone", text)


class EigenesLayoutTest(FlaskFall):
    """Der Layout-Seam: die Anwendung verdraengt das Template der Bibliothek."""

    eigenes_layout = True

    def test_app_layout_gewinnt(self):
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn("marke-der-anwendung", text)
        self.assertNotIn("wc-standalone", text)

    def test_inhalt_ist_trotzdem_da(self):
        text = self.client.get("/neuigkeiten").get_data(as_text=True)
        self.assertIn("v0.5.0", text)
        self.assertIn("Fuenf-Null-Neuerung.", text)


class DialogAbschaltbarTest(FlaskFall):
    dialog = False

    def test_kein_dialog_und_kein_cookie(self):
        antwort = self.client_mit_gesehener_version("0.4.0").get("/")
        self.assertNotIn("wc-dialog", antwort.get_data(as_text=True))
        self.assertNotIn("wc_gesehen", antwort.headers.get("Set-Cookie", ""))

    def test_seite_bleibt(self):
        self.assertEqual(self.client.get("/neuigkeiten").status_code, 200)


class FehlendesChangelogTest(unittest.TestCase):
    def test_anwendung_startet_trotzdem(self):
        app = Flask(__name__)
        changelogs = Changelogs(app, pfad="/gibt/es/nicht/CHANGELOG.md")
        self.assertIsNone(changelogs.aktuelle_version)
        self.assertEqual(app.test_client().get("/neuigkeiten").status_code, 200)


if __name__ == "__main__":
    unittest.main()
