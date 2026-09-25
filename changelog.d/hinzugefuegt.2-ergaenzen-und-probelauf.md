`freeze-changelog` kennt zwei neue Optionen. Mit `--ergaenzen` sortiert es
Fragmente in einen bereits vorhandenen Versionsblock ein, statt sie liegen zu
lassen; das hilft, wenn während eines laufenden Versionswechsels noch Änderungen
dazukommen. Mit `--dry-run` zeigt es den Block, der entstehen würde, ohne die
Datei zu ändern und ohne Fragmente zu löschen.
