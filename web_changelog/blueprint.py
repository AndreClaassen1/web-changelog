"""Flask-Anbindung: Blueprint, Seite, Dialog.

Die Anwendung erzeugt eine ``Changelogs``-Instanz und ergaenzt zwei Aufrufe in
ihrem Layout. Alles Weitere -- Route, Cookie, Entscheidung, Markup -- liegt hier.
"""

from __future__ import annotations

from pathlib import Path

from flask import Blueprint, Flask, Response, g, render_template, request, url_for
from markupsafe import Markup

from .model import Changelog
from .parser import lade
from .speicher import CookieSpeicher
from .version import Versionsnummer
from .vokabular import VOKABULAR_KAC, Vokabular
from .whatsnew import Faellig, Speicher, hole_faellige

_BLUEPRINT_NAME = "web_changelog"
_G_FAELLIG = "_wc_faellig"


def _asset_stand() -> dict[str, int]:
    """mtime der mitgelieferten Dateien, einmal beim Import."""
    ordner = Path(__file__).parent / "static/web_changelog"
    stand = {}
    for name in ("changelog.css", "dialog.js"):
        try:
            stand[name] = int((ordner / name).stat().st_mtime)
        except OSError:
            stand[name] = 0
    return stand


_ASSET_STAND = _asset_stand()


class Changelogs:
    """Changelog-Seite und Was-ist-neu-Dialog fuer eine Flask-Anwendung.

    :param app: die Anwendung; kann auch spaeter ueber ``init_app`` folgen.
    :param pfad: Pfad zur ``CHANGELOG.md``.
    :param vokabular: Rubriken-Vokabular der Anwendung.
    :param pfad_seite: URL der Verlaufsseite.
    :param app_name: Anzeigename im Dialogtitel.
    :param version: laufende Version; ohne Angabe der oberste Changelog-Eintrag.
    :param dialog: auf ``False`` bleibt nur die Seite, ohne Cookie und Dialog.
    :param cookie_secure: Cookie nur ueber HTTPS ausliefern.
    :param speicher: eigener Speicher, etwa am Nutzerprofil statt im Cookie.
        Verdraengt ``cookie_secure``, weil dieses nur den Standardspeicher
        betrifft.
    """

    def __init__(
        self,
        app: Flask | None = None,
        *,
        pfad: Path | str,
        vokabular: Vokabular = VOKABULAR_KAC,
        pfad_seite: str = "/neuigkeiten",
        app_name: str = "",
        version: str | None = None,
        dialog: bool = True,
        speicher: Speicher | None = None,
        cookie_secure: bool = False,
    ) -> None:
        self.pfad = Path(pfad)
        self.vokabular = vokabular
        self.pfad_seite = pfad_seite
        self.app_name = app_name
        self.dialog_aktiv = dialog
        self.speicher = speicher or CookieSpeicher(secure=cookie_secure)
        self._version_override = version
        self._changelog: Changelog | None = None

        if app is not None:
            self.init_app(app)

    # -- Daten ---------------------------------------------------------------

    @property
    def changelog(self) -> Changelog:
        """Das geparste Changelog, einmalig gelesen.

        Die Datei aendert sich zur Laufzeit nicht: sie liegt im Wheel und ein
        Deploy startet den Prozess ohnehin neu.
        """
        if self._changelog is None:
            self._changelog = lade(self.pfad)
        return self._changelog

    @property
    def aktuelle_version(self) -> Versionsnummer | None:
        if self._version_override is not None:
            return Versionsnummer.parse(self._version_override)
        return self.changelog.neueste_nummer

    # -- Verdrahtung ---------------------------------------------------------

    def init_app(self, app: Flask) -> None:
        blueprint = Blueprint(
            _BLUEPRINT_NAME,
            __name__,
            template_folder="templates",
            static_folder="static",
            static_url_path="/_web_changelog/static",
        )
        blueprint.add_url_rule(self.pfad_seite, endpoint="seite", view_func=self._seite)
        app.register_blueprint(blueprint)

        app.jinja_env.globals["wc_head"] = self._head
        app.jinja_env.globals["wc_whatsnew"] = self._whatsnew

        if self.dialog_aktiv:
            app.after_request(self._nach_request)

        app.extensions.setdefault("web_changelog", self)

    # -- Ansichten -----------------------------------------------------------

    def _seite(self) -> str:
        # Die Seite zeigt den vollen Verlauf. Der Dialog waere hier doppelt --
        # gemerkt wird die Version trotzdem, siehe _faellig().
        self._faellig()
        return render_template(
            "web_changelog/seite.html",
            layout_template="web_changelog/layout.html",
            changelog=self.changelog,
            vokabular=self.vokabular,
            app_name=self.app_name,
            aktuelle_version=self.aktuelle_version,
        )

    def _head(self) -> Markup:
        url = self._asset_url("changelog.css")
        return Markup(f'<link rel="stylesheet" href="{url}">')

    def _asset_url(self, name: str) -> str:
        """URL einer mitgelieferten Datei mit Cache-Buster aus ihrer mtime.

        Der Buster stammt aus ``_ASSET_STAND``, das beim Import einmal ermittelt
        wird: die Dateien liegen im Wheel und aendern sich zur Laufzeit nicht,
        ein Deploy startet den Prozess ohnehin neu. Ein ``stat()`` je gerenderter
        Seite waere der einzige Datei-Zugriff im Request-Pfad, und ein
        vermeidbarer.
        """
        return url_for(
            f"{_BLUEPRINT_NAME}.static",
            filename=f"web_changelog/{name}",
            v=_ASSET_STAND.get(name, 0),
        )

    def _whatsnew(self) -> Markup:
        """Dialog-Markup, oder leer wenn nichts anliegt."""
        faellig = self._faellig()
        # Auf der Verlaufsseite unterdrueckt: dort stuende dasselbe zweimal.
        # Ueber den Endpunkt statt ueber den Pfad, damit es auch dann greift,
        # wenn die Anwendung unter einem Unterpfad haengt (SCRIPT_NAME).
        if faellig is None or request.endpoint == f"{_BLUEPRINT_NAME}.seite":
            return Markup("")
        return Markup(render_template(
            "web_changelog/dialog.html",
            faellig=faellig,
            rubriken=faellig.zusammengefasst(self.vokabular),
            vokabular=self.vokabular,
            app_name=self.app_name,
            dialog_js=self._asset_url("dialog.js"),
        ))

    # -- Innereien -----------------------------------------------------------

    def _faellig(self) -> Faellig | None:
        """Ermittelt einmal pro Request, was anliegt.

        Der Cache in ``g`` ist nicht nur Sparsamkeit: ``hole_faellige`` merkt
        sich die Version als Seiteneffekt, ein zweiter Aufruf im selben Request
        wuerde deshalb ``None`` liefern und den Dialog verschlucken.
        """
        if not self.dialog_aktiv:
            return None
        if not hasattr(g, _G_FAELLIG):
            aktuell = self.aktuelle_version
            faellig = None
            if aktuell is not None:
                faellig = hole_faellige(self.speicher, aktuell, lambda: self.changelog)
            setattr(g, _G_FAELLIG, faellig)
        return getattr(g, _G_FAELLIG)

    def _nach_request(self, antwort: Response) -> Response:
        schreiber = getattr(self.speicher, "schreibe_in", None)
        return schreiber(antwort) if schreiber is not None else antwort
