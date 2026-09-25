# Änderungshistorie

Alle nennenswerten Änderungen an diesem Paket. Format nach
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), Versionierung nach
[Semantic Versioning](https://semver.org/lang/de/).

Offene Einträge liegen als Fragmente in `changelog.d/` und werden beim
Versions-Bump von `bin/freeze-changelog` hier eingefroren.

## [Unreleased]

## [0.1.0] – 2026-07-31

### Hinzugefügt

- Changelog-Seite und „Was ist neu"-Dialog für Flask-Anwendungen, portiert vom
  Swift-Paket AppChangelog.
- Parser für das Keep-a-Changelog-Format, der deutsche und englische Rubriken
  erkennt und umbrochene Aufzählungspunkte zusammenhält.
- Konfigurierbares Rubriken-Vokabular, damit eine Anwendung ihre eigenen
  Bezeichnungen verwenden kann, ohne die Semantik zu verlieren.
- Format-Gate `pruefe()`, das eine Anwendung auf ihr Vokabular festlegen kann.
- `freeze-changelog` als Modul, damit Projekte kein eigenes Skript mehr pflegen.
