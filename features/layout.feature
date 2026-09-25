Feature: Einbindung in das Layout der Anwendung
  Als Entwickler möchte ich die Neuigkeitenseite in mein bestehendes Design
  einhängen, ohne dafür ein gemeinsames Basis-Template zu brauchen.

  Scenario: Anwendung ohne eigenes Layout
    Given eine Anwendung ohne eigenes Basis-Template
    When ich die Neuigkeitenseite aufrufe
    Then bekomme ich eine vollständige, eigenständige Seite

  Scenario: Anwendung mit eigenem Layout
    Given eine Anwendung mit eigenem Basis-Template
    When ich die Neuigkeitenseite aufrufe
    Then trägt die Seite das Design der Anwendung
    And enthält sie trotzdem den vollen Verlauf

  Scenario: Eigene Rubrikbezeichnungen
    Given eine Anwendung mit dem Vokabular "anwender"
    When ich die Neuigkeitenseite aufrufe
    Then heißt die Rubrik "Verbessert"
    And trägt sie die Kennzeichnung "wc-badge-geaendert"
