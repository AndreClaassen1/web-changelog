"""Schritte fuer Eintraege, die aus mehreren Absaetzen bestehen."""

import re

from behave import given, then
from environment import antworttext, sicherstellen

from web_changelog.testing import CHANGELOG_ABSAETZE


@given('eine Anwendung mit einem ausführlichen Eintrag')
def schritt_ausfuehrlicher_eintrag(context):
    sicherstellen(context, changelog=CHANGELOG_ABSAETZE)


@then('steht beides in einem Aufzählungspunkt')
def schritt_ein_punkt(context):
    punkte = re.findall(r"<li>.*?</li>", antworttext(context), re.DOTALL)
    treffer = [p for p in punkte if "Ratsvorlage" in p]
    assert len(treffer) == 1, f"erwartet ein li mit dem Eintrag, gefunden {len(treffer)}"
    assert "250.000 Euro" in treffer[0], "der Folgeabsatz steht in einem anderen Punkt"
