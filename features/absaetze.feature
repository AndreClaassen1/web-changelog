Feature: Einträge mit mehreren Absätzen
  Als Leserin der Neuigkeiten möchte ich einen ausführlichen Eintrag
  vollständig sehen, auch wenn er aus mehreren Absätzen besteht.

  Beim Release 1.1.0 von digitale-rendite verlor ein solcher Eintrag seinen
  Risikoabschnitt und die Eurobeträge, ohne dass es jemandem auffiel.

  Scenario: Der Folgeabsatz erscheint auf der Verlaufsseite
    Given eine Anwendung mit einem ausführlichen Eintrag
    When ich die Neuigkeitenseite aufrufe
    Then sehe ich "Ratsvorlage als Entwurf gekennzeichnet."
    And sehe ich "Der Risikoabschnitt weist bis zu 250.000 Euro aus."
    And steht beides in einem Aufzählungspunkt

  Scenario: Der Folgeabsatz erscheint auch im Hinweis
    Given eine Anwendung mit einem ausführlichen Eintrag
    And ich habe zuletzt Version "0.4.0" gesehen
    When ich die Startseite aufrufe
    Then sehe ich einen Hinweis auf Neuerungen
    And sehe ich "Der Risikoabschnitt weist bis zu 250.000 Euro aus."
