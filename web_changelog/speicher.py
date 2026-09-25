"""Ablage der zuletzt gesehenen Version.

Standardweg ist ein eigenes, langlebiges Cookie. Bewusst **nicht** die
Flask-Session: nicht jede Anwendung hat einen ``SECRET_KEY``, und wo die Session
an serverseitige Daten gekoppelt ist, verlaengert eine dauerhafte Session deren
Lebensdauer ungewollt mit. Ein Wert ohne Schutzbedarf gehoert ohnehin nicht in
einen signierten Behaelter.
"""

from __future__ import annotations

import re

from flask import Response, g, request

#: Nur Ziffern und Punkte, kurz begrenzt. Ein manipuliertes Cookie soll als
#: "nichts gemerkt" gelten statt einen Fehler auszuloesen -- der schlimmste
#: Schaden ist ein Dialog zu viel.
_PLAUSIBEL = re.compile(r"^\d{1,4}(\.\d{1,4}){0,3}$")

#: Schluessel, unter dem der Schreibwunsch bis zum Antwortende in ``g`` liegt.
_G_SCHLUESSEL = "_wc_zu_merken"


class CookieSpeicher:
    """Liest aus dem Request-Cookie, schreibt ueber ``after_request``.

    ``merke()`` schreibt nicht sofort, sondern hinterlegt den Wunsch in ``g``.
    Das ist noetig, damit die Regel "merken vor entscheiden" aus
    ``whatsnew.hole_faellige`` im Request-Zyklus tragen kann: zum Zeitpunkt der
    Entscheidung existiert die Antwort noch gar nicht.
    """

    def __init__(self, name: str = "wc_gesehen", max_age: int = 365 * 24 * 3600,
                 secure: bool = False, samesite: str = "Lax") -> None:
        self.name = name
        self.max_age = max_age
        self.secure = secure
        self.samesite = samesite

    def lies(self) -> str | None:
        roh = request.cookies.get(self.name)
        if roh is None or not _PLAUSIBEL.match(roh):
            return None
        return roh

    def merke(self, version: str) -> None:
        setattr(g, _G_SCHLUESSEL, version)

    def schreibe_in(self, antwort: Response) -> Response:
        """Setzt das Cookie auf die Antwort, wenn es etwas zu merken gibt.

        Nur auf Antworten, die der Besucher auch gesehen haben kann: ein
        Redirect, ein JSON-Endpunkt oder ein Health-Check wuerde die Version
        sonst still wegquittieren, und die Neuerungen waeren verbraucht, ohne
        dass sie jemand zu Gesicht bekommen hat.
        """
        version = getattr(g, _G_SCHLUESSEL, None)
        if version is None:
            return antwort
        if request.method != "GET" or antwort.status_code != 200:
            return antwort
        if antwort.mimetype != "text/html":
            return antwort

        antwort.set_cookie(
            self.name,
            version,
            max_age=self.max_age,
            httponly=True,
            secure=self.secure,
            samesite=self.samesite,
        )
        # Ohne Vary liefert ein Proxy die Dialog-Variante an alle aus.
        antwort.headers.add("Vary", "Cookie")
        return antwort
