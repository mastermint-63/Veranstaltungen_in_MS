# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektbeschreibung

Veranstaltungs-Dashboard für das Münsterland. Sammelt Events von zwei Quellen:
- **muensterland.com** (Datenportal-API): Allgemeine Veranstaltungen
- **Digital Hub münsterLAND** (digitalhub.ms API): Startup- und Tech-Events

Generiert verlinkte HTML-Dashboards mit Monatsnavigation und Filterfunktion.

## Ausführung

```bash
python3 app.py                    # 3 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 3 Monate ab Feb 2026
python3 app.py 2026 1 12          # 12 Monate (ganzes Jahr)
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Manuell aktualisieren (mit macOS-Benachrichtigung)
./oeffne_aktuell.sh               # Aktuellen Monat im Browser öffnen
```

## Automatische Aktualisierung

Launchd-Job läuft täglich um 6:15 Uhr und beim Systemstart (RunAtLoad):
- Plist: `~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist`
- Log: `launchd.log` (im Projektverzeichnis)
- ThrottleInterval: 6 Stunden (verhindert doppelte Ausführung)

```bash
launchctl list | grep veranstaltungen                    # Status prüfen
launchctl start de.veranstaltungen-ms.update             # Manuell auslösen
launchctl unload ~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist  # Deaktivieren
launchctl load ~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist    # Aktivieren
tail -f launchd.log                                      # Live-Log anzeigen
```

### Benachrichtigungen

`update.sh` sendet macOS-Notifications mit:
- Event-Anzahl und Differenz zum vorherigen Stand (+X neu / -X weniger / unverändert)
- Fehlermeldungen bei API-Timeouts (⚠️ mit Basso-Sound)
- Erfolgsbestätigung (✅ mit Glass-Sound)

Benachrichtigungen erscheinen oben rechts in der Mitteilungszentrale.

## Architektur

**Datenfluss:** API → scraper.py → app.py → HTML-Dateien

### scraper.py
Zwei API-Clients für verschiedene Datenquellen:

#### 1. `hole_veranstaltungen(jahr, monat)` - Münsterland Events
- POST-Request an `https://www.muensterland.com/dpms/`
- Paginierung: 100 Events/Seite, automatisches Durchlaufen aller Seiten
- Laufende Events aus Vormonaten werden auf den 1. des Monats mit Uhrzeit "laufend" gesetzt
- Timeout-Handling: 30 Sekunden, bricht bei Fehler ab (verhindert unvollständige Daten)

#### 2. `hole_digitalhub_events(jahr, monat)` - Digital Hub Events
- GET-Request an `https://www.digitalhub.ms/api/events?api_token=XXX`
- Öffentlicher Demo-API-Key: `089d362b33ef053d7fcd241d823d27d1`
- Response-Format: `{"data": [...]}`
- Filtert Events nach Monat (API liefert alle zukünftigen Events)
- Markiert Events mit `quelle='digitalhub'` und `kategorie` (z.B. "Hub-Event · Workshop")

**Rückgabe beider Funktionen:** Liste von `Veranstaltung`-Dataclass-Objekten

### app.py
Dashboard-Generator:
- `generiere_kalender(jahr, monat, tage_mit_events)` — erzeugt HTML-Tabelle (Mo–So) mit Anker-Links
- Ruft `scraper.hole_veranstaltungen()` und `scraper.hole_digitalhub_events()` für jeden Monat auf
- Kombiniert beide Datenquellen zu einer Liste
- Gruppiert Events nach Datum (`id="datum-YYYY-MM-DD"` für Kalender-Anker), sortiert nach Uhrzeit
- Events mit `external_link` → normaler Link; Events ohne Link → aufklappbar (Toggle mit vollständiger Beschreibung)
- Generiert statische HTML-Dateien mit:
  - Eingebettetem CSS (Apple-Design, Dark Mode Support)
  - Kalenderblatt mit klickbaren Tagen
  - JavaScript für Stadt- und Quellen-Filter
  - Badges für Digital Hub Events (🚀 Digital Hub + Kategorie)
  - Monatsnavigation (← →) mit Verfügbarkeitsprüfung
  - Live-Statistik (Anzahl sichtbare Events)
- Dateinamen: `veranstaltungen_YYYY_MM.html`

### update.sh
Automatisierungs-Wrapper:
- Liest alte Event-Anzahl aus bestehenden HTML-Dateien (via grep auf `<span id="termine-count">`)
- Führt `app.py --no-browser` aus
- Berechnet Differenz (neu vs. alt)
- Erkennt API-Fehler im Output (`grep "Fehler beim Abrufen"`)
- Sendet macOS-Notification mit osascript

## Datenquellen

### 1. Münsterland Events (muensterland.com)

JSON-API via POST an `https://www.muensterland.com/dpms/` (Proxy für Datenportal Münsterland).

Parameter:
- `endpoint=events`
- `page[size]=100`, `page[number]=1`
- `returnFormat=json`
- `from=YYYY-MM-DD`, `to=YYYY-MM-DD`

Response enthält: name, start_datetime, end_datetime, poi (Ort/Adresse), description_text, external_link.

**Hinweis zu Links:** Die API hat kein Feld für Event-Detailseiten auf muensterland.com. Nur `external_link` (Link zur Veranstalter-Website) ist nutzbar. Events ohne `external_link` werden im Dashboard aufklappbar dargestellt mit vollständiger Beschreibung.

### 2. Digital Hub münsterLAND (digitalhub.ms)

JSON-API via GET an `https://www.digitalhub.ms/api/events`.

Parameter:
- `api_token=089d362b33ef053d7fcd241d823d27d1` (öffentlicher Demo-Key)
- Optional: `city`, `mode`, `hub_event`, `district`, `interest`

Response-Format:
```json
{
  "data": [
    {
      "id": 2252,
      "title": "Event-Name",
      "start_date": "2026-03-02",
      "start_time": "09:00",
      "end_time": "16:00",
      "address": "Adresse",
      "city": "Münster",
      "district": "MS",
      "mode": "Workshop",
      "flag": "Hub-Event",
      "link_url": "https://...",
      "desc": "Beschreibung",
      "organizer": "Digital Hub münsterLAND"
    }
  ]
}
```

**Dokumentation:** [digitalhub.ms/api](https://www.digitalhub.ms/api)

## HTML-Dashboard Features

Generierte Dateien (`veranstaltungen_YYYY_MM.html`) sind vollständig standalone:
- **Keine externen Dependencies**: CSS und JavaScript sind eingebettet
- **Dark Mode**: Automatische Anpassung an System-Präferenz via `prefers-color-scheme`
- **Kalenderblatt**: Monatskalender (Mo–So) oberhalb der Events, Tage mit Events als grüne Kreise anklickbar, springt per Anker (`#datum-YYYY-MM-DD`) zum jeweiligen Datum
- **Zwei Filter**: Stadt (Dropdown) + Quelle (Münsterland/Digital Hub)
- **Event-Badges**: Digital Hub Events haben visuell unterscheidbare Badges (🚀 + Kategorie)
- **Aufklappbare Details**: Events ohne externen Link zeigen den Namen mit ▸-Pfeil; Klick klappt die vollständige Beschreibung auf (statt auf nicht-funktionierende URLs zu verlinken)
- **Live-Statistik**: JavaScript aktualisiert Event-Anzahl bei Filterung
- **Monatsnavigation**: Verlinkte Pfeile (← →) mit automatischer Verfügbarkeitsprüfung

## Multi-Source-Strategie

Beide API-Quellen werden **parallel** abgefragt und zu einer gemeinsamen Liste zusammengeführt:
1. `scraper.hole_veranstaltungen(jahr, monat)` läuft unabhängig
2. `scraper.hole_digitalhub_events(jahr, monat)` läuft unabhängig
3. `app.py` kombiniert beide Listen mit `veranstaltungen.extend(digitalhub_events)`
4. Fehler in einer Quelle beeinflussen die andere nicht

**Wichtig beim Hinzufügen neuer Quellen:**
- Neue Funktion in `scraper.py` mit gleichem Rückgabetyp (`list[Veranstaltung]`)
- Import in `app.py` hinzufügen
- In der Hauptschleife von `app.py` aufrufen und mit `.extend()` anhängen
- `quelle`-Parameter setzen für visuell unterscheidbare Darstellung

## Fehlerbehandlung

- **API-Timeouts**: scraper.py bricht nach 30s ab, protokolliert Fehler, generiert HTML mit bisherigen Events
- **Unvollständige Daten**: update.sh erkennt Fehler im Output und sendet Warn-Notification
- **Verpasste Launchd-Runs**: RunAtLoad sorgt für Nachholen beim nächsten Systemstart
- **Partielle Fehler**: Wenn eine API fehlschlägt, werden trotzdem Events aus den anderen Quellen angezeigt
