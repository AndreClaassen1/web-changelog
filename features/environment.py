"""Behave-Hooks: baut je Szenario eine Wegwerf-Anwendung.

Der Aufbau selbst liegt in ``web_changelog.testing``, damit Unit- und
Akzeptanztests gegen dasselbe Changelog laufen.
"""

import shutil

from web_changelog.testing import baue_anwendung
from web_changelog.vokabular import VOKABULAR_ANWENDER, VOKABULAR_KAC

VOKABULARE = {"anwender": VOKABULAR_ANWENDER, "kac": VOKABULAR_KAC}


def sicherstellen(context, **kwargs):
    """Legt die Anwendung an, falls ein Szenario direkt mit einem Besuch startet.

    Nur beim ersten Aufruf: ein zweiter Aufbau wuerde den Client samt gesetzter
    Cookies wegwerfen.
    """
    if context.app is None:
        context.app, context.wurzel = baue_anwendung(**kwargs)
        context.client = context.app.test_client()


def antworttext(context):
    return context.antwort.get_data(as_text=True)


def before_scenario(context, scenario):
    context.app = None
    context.wurzel = None
    context.client = None
    context.antwort = None


def after_scenario(context, scenario):
    if context.wurzel is not None:
        shutil.rmtree(context.wurzel, ignore_errors=True)
