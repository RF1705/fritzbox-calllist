# Telefon Feed

Eine HACS-fähige Home-Assistant-Custom-Integration für FRITZ!Box-Callmonitor-Sensoren.

Du wählst nur den vorhandenen Callmonitor-Sensor aus. Die Integration erstellt daraus:

- einen Feed-Sensor mit Anrufverlauf
- Live-Status für klingelnde, ausgehende und aktive Anrufe
- Anrufdauer für Live-Anrufe und abgeschlossene Gespräche
- eine eigene Lovelace-Karte ohne Markdown-Abhängigkeit

## Installation

1. Dieses Repository in HACS als benutzerdefiniertes Repository hinzufügen.
2. Kategorie `Integration` auswählen.
3. Integration installieren.
4. Home Assistant neu starten.
5. Unter **Einstellungen > Geräte & Dienste > Integration hinzufügen** nach `Telefon Feed` suchen.
6. Deinen FRITZ!Box-Callmonitor-Sensor auswählen.

## Lovelace-Karte

Nach der Einrichtung wird das Kartenmodul automatisch registriert. Falls dein Browser die Ressource noch nicht kennt, lade Home Assistant einmal hart neu.

Falls die Karte danach noch nicht auftaucht, fuege unter **Einstellungen > Dashboards > Ressourcen** manuell diese JavaScript-Modul-Ressource hinzu:

```text
/telefon_feed/telefon-feed-card.js
```

```yaml
type: custom:telefon-feed-card
entity: sensor.telefon_feed
title: Telefon
max_items: 4
```

Während eines Live-Anrufs zeigt die Karte automatisch einen Eintrag weniger im Verlauf an.

## Optionen

Die Integration kann über den Konfigurationsdialog angepasst werden:

- Callmonitor-Sensor
- Anzahl gespeicherter Einträge
