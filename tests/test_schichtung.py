"""Waechter ueber die Trennlinie zu Flask.

Parser, Vokabular, Pruefung, Versionslogik und das Freeze-Skript sollen ohne
Web-Kontext benutzbar bleiben: in Skripten, in der CI, in anderen Projekten.
Ein versehentliches ``from flask import ...`` in einem dieser Module faellt hier
auf und nicht erst beim Nutzer.
"""

import ast
import unittest

from pathlib import Path

PAKET = Path(__file__).resolve().parent.parent / "web_changelog"

#: Die einzigen Module, die Flask sehen duerfen. ``testing.py`` gehoert dazu,
#: weil es Flask-Testanwendungen baut; es wird zur Laufzeit nie importiert.
MIT_FLASK = {"speicher.py", "blueprint.py", "testing.py"}


def _importierte_namen(pfad: Path) -> set[str]:
    baum = ast.parse(pfad.read_text(encoding="utf-8"), filename=str(pfad))
    namen: set[str] = set()
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Import):
            namen.update(a.name.split(".")[0] for a in knoten.names)
        elif isinstance(knoten, ast.ImportFrom) and knoten.module and knoten.level == 0:
            namen.add(knoten.module.split(".")[0])
    return namen


class TrennlinieTest(unittest.TestCase):
    def test_kern_ohne_flask(self):
        for pfad in sorted(PAKET.glob("*.py")):
            if pfad.name in MIT_FLASK:
                continue
            with self.subTest(modul=pfad.name):
                namen = _importierte_namen(pfad)
                self.assertNotIn("flask", namen, f"{pfad.name} importiert Flask")
                self.assertNotIn("markupsafe", namen, f"{pfad.name} importiert markupsafe")

    def test_kern_zieht_flask_nicht_mit(self):
        # __init__ laedt Changelogs erst bei Bedarf nach, damit das
        # Freeze-Skript und ein Format-Gate in der CI ohne Web-Kontext
        # auskommen. Ein frischer Interpreter beweist es; im laufenden Prozess
        # haben andere Tests Flask laengst importiert.
        import subprocess
        import sys

        code = "import sys, web_changelog; print('flask' in sys.modules)"
        ausgabe = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, check=True
        )
        self.assertEqual(ausgabe.stdout.strip(), "False")

    def test_changelogs_bleibt_erreichbar(self):
        import web_changelog

        self.assertTrue(callable(web_changelog.Changelogs))

    def test_unbekannter_name_wirft(self):
        import web_changelog

        with self.assertRaises(AttributeError):
            web_changelog.gibt_es_nicht


if __name__ == "__main__":
    unittest.main()
