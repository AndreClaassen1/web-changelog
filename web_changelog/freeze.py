"""Friert die offenen Changelog-Eintraege auf eine Version ein.

Portierung des Skripts ``bin/freeze-changelog``, das bisher in jedem Projekt als
Kopie lag. Verhalten und Ausgabe bleiben fuer ``VOKABULAR_KAC`` unveraendert,
damit die vorhandenen Repos nicht auseinanderdriften; neu ist allein, dass das
Rubriken-Vokabular waehlbar ist.

Hintergrund: Der ``[Unreleased]``-Block ist eine einzige Stelle, in die jeder
Branch schreibt. Arbeiten mehrere Worktrees parallel, kollidieren sie dort fast
bei jedem Merge. Eine Datei je Aenderung loest das strukturell: zwei Branches
beruehren nie dieselbe Datei.

Datiert werden kann der Block erst, wenn die Zielnummer feststeht. Deshalb
gehoert dieser Schritt in den Versions-Bump und nicht in den Feature-Branch.

Quellen der Eintraege (beide werden zusammengefuehrt):

1. ``changelog.d/`` -- eine Datei je Aenderung, benannt ``<rubrik>.<slug>.md``.
   Das ist der empfohlene Weg.
2. Direkt unter ``## [Unreleased]`` geschriebene Eintraege -- weiter zulaessig,
   damit ein schneller Einzeiler moeglich bleibt.

Verhalten:

* Gibt es weder Fragmente noch Inhalt unter ``[Unreleased]``, passiert nichts.
  Ein Infrastruktur-Release ohne sichtbare Aenderung bekommt keinen leeren Block.
* Existiert bereits ein Block zur Zielversion, bleibt alles unveraendert und die
  Fragmente bleiben liegen. Der Aufruf ist damit wiederholbar. Mit
  ``--ergaenzen`` werden sie stattdessen in den vorhandenen Block einsortiert --
  gedacht fuer den Fall, dass waehrend eines laufenden Bumps weitere Branches mit
  Fragmenten dazukommen.
* ``--dry-run`` zeigt den Block, der entstehen wuerde, schreibt aber nichts und
  loescht keine Fragmente.
* Verarbeitete Fragmente werden geloescht; wer den Bump committet, muss
  ``changelog.d`` deshalb mit ``git add -A`` erfassen.
* Exit-Code ist immer 0, solange die Datei lesbar ist: ein uebersprungener
  Einfrier-Schritt ist kein Fehler und darf den Release nicht aufhalten.
"""

from __future__ import annotations

import argparse
import datetime
import pathlib
import re
import sys

from .vokabular import VOKABULAR_ANWENDER, VOKABULAR_KAC, Art, Vokabular, art_aus_ueberschrift

UNRELEASED = "## [Unreleased]"

#: Trennzeichen zwischen Version und Datum, wenn die Datei noch keines vorgibt.
STANDARD_TRENNER = "–"

VOKABULARE: dict[str, Vokabular] = {
    "kac": VOKABULAR_KAC,
    "anwender": VOKABULAR_ANWENDER,
}

_VORHANDENER_KOPF = re.compile(r"^## \[[^\]]+\]\s*([—–-])\s*\d{4}-\d{2}-\d{2}\s*$", re.MULTILINE)
_NAECHSTER_BLOCK = re.compile(r"^## \[", re.MULTILINE)


def als_aufzaehlung(text: str) -> str:
    """Formt den Fragment-Text zu Changelog-Aufzaehlungspunkten.

    Bringt der Text seine eigenen ``- ``-Punkte mit, bleibt er unangetastet -- so
    behaelt der Autor die Kontrolle ueber Unterpunkte und Absaetze. Reine Prosa
    wird zu einem Punkt mit zwei Leerzeichen Fortsetzungseinzug.
    """
    zeilen = [z.rstrip() for z in text.strip().splitlines()]
    if not zeilen:
        return ""
    if zeilen[0].lstrip().startswith("- "):
        return "\n".join(zeilen)
    return "\n".join([f"- {zeilen[0]}"] + [f"  {z}" if z else "" for z in zeilen[1:]])


def trenner_aus_datei(text: str) -> str:
    """Uebernimmt das Trennzeichen des obersten vorhandenen Versionskopfes.

    Ohne das mischt eine Datei, die durchgehend den Geviertstrich nutzt, ab dem
    ersten eingefrorenen Block zwei Schreibweisen.
    """
    treffer = _VORHANDENER_KOPF.search(text)
    return treffer.group(1) if treffer else STANDARD_TRENNER


def _versionskopf(text: str, version: str) -> re.Match[str] | None:
    """Findet die Ueberschriftszeile eines Versionsblocks, oder None."""
    return re.search(rf"^## \[{re.escape(version)}\].*$", text, re.MULTILINE)


def _rumpf_ende(text: str, ab: int) -> int:
    """Ende des Rumpfes, der bei ``ab`` beginnt.

    Reicht bis zur naechsten Versionsueberschrift, sonst bis zum Dateiende.
    """
    naechste = _NAECHSTER_BLOCK.search(text, ab)
    return naechste.start() if naechste else len(text)


def _verschmelze(ziel: dict[Art, list[str]], zusatz: dict[Art, list[str]]) -> None:
    """Haengt die Eintraege aus ``zusatz`` je Art an ``ziel`` an."""
    for art, inhalte in zusatz.items():
        ziel.setdefault(art, []).extend(inhalte)


def _zaehle_punkte(eintraege: dict[Art, list[str]]) -> str:
    """'1 Eintrag' oder 'n Eintraege' -- gezaehlt werden Aufzaehlungspunkte.

    Nicht die Bloecke je Rubrik: ein Block kann mehrere ``- ``-Zeilen tragen,
    und die Meldung soll nicht weniger nennen, als hinzukommt.
    """
    anzahl = sum(
        1
        for inhalte in eintraege.values()
        for inhalt in inhalte
        for zeile in inhalt.splitlines()
        if zeile.startswith(("- ", "* "))
    )
    return f"{anzahl} Eintrag" if anzahl == 1 else f"{anzahl} Eintraege"


def lies_fragmente(
    verzeichnis: pathlib.Path, vokabular: Vokabular
) -> tuple[dict[Art, list[str]], list[pathlib.Path], list[str]]:
    """Liefert (Eintraege je Art, gelesene Dateien, Warnungen)."""
    eintraege: dict[Art, list[str]] = {}
    dateien: list[pathlib.Path] = []
    warnungen: list[str] = []

    if not verzeichnis.is_dir():
        return eintraege, dateien, warnungen

    for pfad in sorted(verzeichnis.glob("*.md")):
        if pfad.name.startswith(".") or pfad.name.lower() == "readme.md":
            continue
        slug = pfad.name.split(".", 1)[0].lower()
        art = vokabular.art_fuer_slug(slug)
        if art is None:
            erlaubt = ", ".join(vokabular.slugs())
            warnungen.append(
                f"{pfad.name}: unbekannte Rubrik '{slug}' — Datei bleibt liegen "
                f"(erlaubt: {erlaubt})"
            )
            continue
        inhalt = als_aufzaehlung(pfad.read_text(encoding="utf-8"))
        if not inhalt:
            warnungen.append(f"{pfad.name}: leer — Datei bleibt liegen")
            continue
        eintraege.setdefault(art, []).append(inhalt)
        dateien.append(pfad)

    return eintraege, dateien, warnungen


def teile_nach_rubrik(body: str) -> tuple[str, dict[Art, list[str]], dict[Art, str]]:
    """Zerlegt einen ``[Unreleased]``-Rumpf.

    Liefert (Vorspann, Eintraege je Art, rohe Ueberschrift je Art). Der Vorspann
    ist alles vor der ersten ``### ``-Ueberschrift -- normalerweise leer, wird
    aber nicht verworfen, damit nichts still verlorengeht.
    """
    eintraege: dict[Art, list[str]] = {}
    ueberschriften: dict[Art, str] = {}
    teile = re.split(r"^### +(.+?) *$", body, flags=re.MULTILINE)
    vorspann = teile[0].strip()
    for ueberschrift, inhalt in zip(teile[1::2], teile[2::2]):
        inhalt = inhalt.strip()
        if inhalt:
            art = art_aus_ueberschrift(ueberschrift)
            eintraege.setdefault(art, []).append(inhalt)
            ueberschriften.setdefault(art, ueberschrift.strip())
    return vorspann, eintraege, ueberschriften


def baue_block(
    vorspann: str,
    eintraege: dict[Art, list[str]],
    ueberschriften: dict[Art, str],
    vokabular: Vokabular,
) -> str:
    """Setzt Vorspann und Rubriken in kanonischer Reihenfolge zusammen."""
    teile = [vorspann] if vorspann else []
    for art in vokabular.sortiere(eintraege):
        titel = vokabular.label(art, roh=ueberschriften.get(art, ""))
        teile.append(f"### {titel}\n\n" + "\n".join(eintraege[art]))
    return "\n\n".join(teile)


def freeze(
    text: str,
    version: str,
    date: str,
    fragmente: dict[Art, list[str]],
    vokabular: Vokabular = VOKABULAR_KAC,
    ergaenze: bool = False,
) -> tuple[str, str]:
    """Liefert (neuer Text, Meldung). Text bleibt unveraendert, wenn nichts zu tun ist.

    Mit ``ergaenze`` werden die offenen Eintraege in einen bereits vorhandenen
    Block zur Zielversion einsortiert, statt den Aufruf zu ueberspringen. Der
    Kopf dieses Blocks bleibt dabei unangetastet: Datum und Schreibweise sind
    bewusst gesetzt und sollen sich durch einen Nachtrag nicht verschieben.
    """

    vorhanden = _versionskopf(text, version)
    if vorhanden is not None and not ergaenze:
        return text, (
            f"Block zu {version} existiert bereits — nichts zu tun "
            f"(mit --ergaenzen einsortieren)"
        )

    unreleased_start = text.find(UNRELEASED)
    if unreleased_start == -1 and vorhanden is None:
        return text, "Kein [Unreleased]-Block gefunden — nichts zu tun"

    # Ohne [Unreleased]-Block (nur beim Ergaenzen erreichbar) tragen die
    # Fragmente den Nachtrag allein.
    offen = None
    if unreleased_start != -1:
        rumpf_start = unreleased_start + len(UNRELEASED)
        offen = (rumpf_start, _rumpf_ende(text, rumpf_start))
    vorspann, eintraege, ueberschriften = teile_nach_rubrik(
        text[offen[0]:offen[1]] if offen else ""
    )
    _verschmelze(eintraege, fragmente)

    if not vorspann and not eintraege:
        return text, "Keine offenen Eintraege — kein Block angelegt"

    if vorhanden is None:
        trenner = trenner_aus_datei(text)
        # Feste Leerzeilen: der Abstand soll unabhaengig davon stimmen, wie viele
        # Leerzeilen in den Quellen standen.
        frozen = (
            f"{UNRELEASED}\n\n"
            f"## [{version}] {trenner} {date}\n\n"
            f"{baue_block(vorspann, eintraege, ueberschriften, vokabular)}\n\n"
        )
        meldung = f"[Unreleased] eingefroren als {version} ({date})"
        return text[:unreleased_start] + frozen + text[offen[1]:], meldung

    zugewachsen = _zaehle_punkte(eintraege)
    ziel_start = vorhanden.end()
    ziel_ende = _rumpf_ende(text, ziel_start)
    alt_vorspann, alt_eintraege, alt_ueberschriften = teile_nach_rubrik(text[ziel_start:ziel_ende])
    _verschmelze(alt_eintraege, eintraege)
    # Die Schreibweise des vorhandenen Blocks gewinnt: sie steht schon in der Datei.
    zusammen = baue_block(
        "\n\n".join(t for t in (alt_vorspann, vorspann) if t),
        alt_eintraege,
        {**ueberschriften, **alt_ueberschriften},
        vokabular,
    )

    # Von hinten nach vorne ersetzen, damit die frueheren Grenzen gueltig bleiben.
    bereiche = [(ziel_start, ziel_ende, f"\n\n{zusammen}\n\n")]
    if offen is not None:
        bereiche.append((*offen, "\n\n"))
    for start, ende, ersatz in sorted(bereiche, key=lambda b: b[0], reverse=True):
        text = text[:start] + ersatz + text[ende:]
    return text, f"Block zu {version} um {zugewachsen} ergaenzt"


def block_text(text: str, version: str) -> str:
    """Der Versionsblock als Text, fuer die Vorschau im Probelauf."""
    kopf = _versionskopf(text, version)
    if kopf is None:
        return ""
    return (kopf.group(0) + text[kopf.end():_rumpf_ende(text, kopf.end())]).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Friert die offenen Changelog-Eintraege auf eine Version ein."
    )
    parser.add_argument("version", help="Zielversion, etwa 0.7.15")
    parser.add_argument("date", nargs="?", default=None, help="Datum ISO, Standard ist heute")
    parser.add_argument("--changelog", default="CHANGELOG.md", help="Pfad zur Changelog-Datei")
    parser.add_argument("--fragments", default="changelog.d", help="Verzeichnis mit den Fragmenten")
    parser.add_argument(
        "--vokabular",
        default="kac",
        choices=sorted(VOKABULARE),
        help="Rubriken-Vokabular: kac (Keep a Changelog) oder anwender (Neu/Verbessert/Behoben)",
    )
    parser.add_argument(
        "--ergaenzen",
        action="store_true",
        help="Einen bereits vorhandenen Block zur Zielversion um die offenen "
             "Eintraege ergaenzen, statt den Aufruf zu ueberspringen",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur zeigen, was entstehen wuerde: nichts schreiben, nichts loeschen",
    )
    args = parser.parse_args(argv)
    vokabular = VOKABULARE[args.vokabular]

    path = pathlib.Path(args.changelog)
    if not path.exists():
        print(f"==> {path} nicht gefunden — Einfrieren uebersprungen")
        return 0

    fragmente, dateien, warnungen = lies_fragmente(pathlib.Path(args.fragments), vokabular)
    for warnung in warnungen:
        print(f"==> Warnung: {warnung}")

    date = args.date or datetime.date.today().isoformat()
    original = path.read_text(encoding="utf-8")
    updated, message = freeze(
        original, args.version, date, fragmente, vokabular, ergaenze=args.ergaenzen
    )

    if updated == original:
        print(f"==> {message}")
        return 0

    if args.dry_run:
        # Der Probelauf zeigt den fertigen Block statt eines Diffs: das ist der
        # Text, den am Ende jemand liest, und er passt in ein CI-Log.
        print(f"==> Probelauf: {message}")
        if dateien:
            print(f"==> {len(dateien)} Fragment(e) wuerden uebernommen und geloescht:")
            for pfad in dateien:
                print(f"    {pfad.name}")
        print(f"==> So saehe {path} aus:\n")
        print(block_text(updated, args.version))
        return 0

    path.write_text(updated, encoding="utf-8")
    for pfad in dateien:
        pfad.unlink()
    if dateien:
        print(f"==> {len(dateien)} Fragment(e) uebernommen und geloescht")
    print(f"==> {message}")
    return 0


def cli() -> None:
    """Konsolen-Einsprungpunkt (``freeze-changelog``)."""
    sys.exit(main())


if __name__ == "__main__":
    cli()
