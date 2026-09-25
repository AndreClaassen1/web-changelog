"""Schritte fuer die Szenarien rund um Neuigkeiten und Layout."""

from behave import given, then, when

from environment import VOKABULARE, antworttext as _text, sicherstellen as _sicherstellen


# -- Given ------------------------------------------------------------------

@given('eine Anwendung mit einem Changelog bis Version "{version}"')
def schritt_anwendung(context, version):
    _sicherstellen(context)
    context.erwartete_version = version


@given('eine Anwendung ohne eigenes Basis-Template')
def schritt_ohne_layout(context):
    _sicherstellen(context, eigenes_layout=False)


@given('eine Anwendung mit eigenem Basis-Template')
def schritt_mit_layout(context):
    _sicherstellen(context, eigenes_layout=True)


@given('eine Anwendung mit dem Vokabular "{name}"')
def schritt_vokabular(context, name):
    _sicherstellen(context, vokabular=VOKABULARE[name])


@given('ich war noch nie da')
def schritt_erstbesuch(context):
    _sicherstellen(context)


@given('ich habe zuletzt Version "{version}" gesehen')
def schritt_gesehene_version(context, version):
    _sicherstellen(context)
    context.client.set_cookie("wc_gesehen", version)


# -- When -------------------------------------------------------------------

@when('ich die Startseite aufrufe')
@when('ich die Startseite erneut aufrufe')
def schritt_startseite(context):
    _sicherstellen(context)
    context.antwort = context.client.get("/")


@when('ich die Neuigkeitenseite aufrufe')
def schritt_neuigkeitenseite(context):
    _sicherstellen(context)
    context.antwort = context.client.get("/neuigkeiten")


@when('ein Health-Check läuft')
def schritt_health(context):
    _sicherstellen(context)
    context.client.get("/api/health")


# -- Then -------------------------------------------------------------------

@then('sehe ich einen Hinweis auf Neuerungen')
def schritt_hinweis_da(context):
    assert "wc-dialog" in _text(context), "Hinweis fehlt"


@then('sehe ich keinen Hinweis auf Neuerungen')
def schritt_kein_hinweis(context):
    assert "wc-dialog" not in _text(context), "Hinweis erschien unerwartet"


@then('meine Version ist als gesehen vermerkt')
def schritt_vermerkt(context):
    gesetzt = context.antwort.headers.get("Set-Cookie", "")
    assert "wc_gesehen=" in gesetzt, f"kein Vermerk gesetzt: {gesetzt!r}"


@then('der Hinweis nennt "{text}"')
@then('nennt der Hinweis "{text}"')
@then('sehe ich "{text}"')
def schritt_text_erscheint(context, text):
    assert text in _text(context), f"{text!r} fehlt in der Ausgabe"


@then('der Hinweis nennt meine vorherige Version "{version}"')
def schritt_vorherige_version(context, version):
    assert version in _text(context), f"vorherige Version {version} fehlt"


@then('erscheint die Rubrik "{rubrik}" genau einmal')
def schritt_rubrik_einmal(context, rubrik):
    anzahl = _text(context).count(f">{rubrik}</span>")
    assert anzahl == 1, f"Rubrik {rubrik} erschien {anzahl}-mal"


@then('sehe ich die Versionen "{versionen}"')
def schritt_versionen(context, versionen):
    text = _text(context)
    for version in (v.strip() for v in versionen.split(",")):
        assert f"v{version}" in text, f"Version {version} fehlt"


@then('bekomme ich eine vollständige, eigenständige Seite')
def schritt_standalone(context):
    text = _text(context)
    assert "<!DOCTYPE html>" in text, "kein vollstaendiges Dokument"
    assert "wc-standalone" in text, "nicht das mitgelieferte Layout"


@then('trägt die Seite das Design der Anwendung')
def schritt_app_design(context):
    text = _text(context)
    assert "marke-der-anwendung" in text, "Layout der Anwendung fehlt"
    assert "wc-standalone" not in text, "mitgeliefertes Layout hat gewonnen"


@then('enthält sie trotzdem den vollen Verlauf')
def schritt_verlauf(context):
    assert "v0.5.0" in _text(context), "Verlauf fehlt"


@then('heißt die Rubrik "{rubrik}"')
def schritt_rubrikname(context, rubrik):
    assert f">{rubrik}</span>" in _text(context), f"Rubrik {rubrik} fehlt"


@then('trägt sie die Kennzeichnung "{klasse}"')
def schritt_kennzeichnung(context, klasse):
    assert klasse in _text(context), f"CSS-Klasse {klasse} fehlt"
