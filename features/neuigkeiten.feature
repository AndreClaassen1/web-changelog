Feature: Neuigkeiten nach einem Update
  Als Nutzerin einer Web-Anwendung möchte ich nach einem Update erfahren,
  was sich geändert hat, ohne den Verlauf selbst suchen zu müssen.

  Background:
    Given eine Anwendung mit einem Changelog bis Version "0.5.0"

  Scenario: Beim ersten Besuch bleibt die Anwendung still
    Given ich war noch nie da
    When ich die Startseite aufrufe
    Then sehe ich keinen Hinweis auf Neuerungen
    But meine Version ist als gesehen vermerkt

  Scenario: Nach einem Update erscheint der Hinweis
    Given ich habe zuletzt Version "0.4.0" gesehen
    When ich die Startseite aufrufe
    Then sehe ich einen Hinweis auf Neuerungen
    And der Hinweis nennt "Fuenf-Null-Neuerung."
    And der Hinweis nennt meine vorherige Version "0.4.0"

  Scenario: Der Hinweis erscheint nur einmal
    Given ich habe zuletzt Version "0.4.0" gesehen
    When ich die Startseite aufrufe
    And ich die Startseite erneut aufrufe
    Then sehe ich keinen Hinweis auf Neuerungen

  Scenario: Übersprungene Versionen werden zusammengefasst
    Given ich habe zuletzt Version "0.3.0" gesehen
    When ich die Startseite aufrufe
    Then nennt der Hinweis "Fuenf-Null-Neuerung."
    And nennt der Hinweis "Vier-Null-Neuerung."
    And erscheint die Rubrik "Neu" genau einmal

  Scenario: Nach einem Rückschritt bleibt die Anwendung still
    Given ich habe zuletzt Version "0.9.0" gesehen
    When ich die Startseite aufrufe
    Then sehe ich keinen Hinweis auf Neuerungen

  Scenario: Der volle Verlauf ist jederzeit erreichbar
    Given ich habe zuletzt Version "0.4.0" gesehen
    When ich die Neuigkeitenseite aufrufe
    Then sehe ich die Versionen "0.5.0, 0.4.0, 0.3.0"
    But sehe ich keinen Hinweis auf Neuerungen

  Scenario: Ein Health-Check verbraucht die Neuerungen nicht
    Given ich habe zuletzt Version "0.4.0" gesehen
    When ein Health-Check läuft
    And ich die Startseite aufrufe
    Then sehe ich einen Hinweis auf Neuerungen
