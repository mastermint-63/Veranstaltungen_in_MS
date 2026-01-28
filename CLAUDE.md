# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektbeschreibung

Veranstaltungs-Dashboard für das Münsterland. Sammelt Events von muensterland.com (Datenportal-API) und generiert verlinkte HTML-Dashboards mit Monatsnavigation.

## Ausführung

```bash
python3 app.py                    # 3 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 3 Monate ab Feb 2026
python3 app.py 2026 1 12          # 12 Monate (ganzes Jahr)
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Manuell aktualisieren (mit macOS-Benachrichtigung)
```

## Automatische Aktualisierung

Launchd-Job läuft täglich um 6:15 Uhr:
- Plist: `~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist`
- Log: `launchd.log`

```bash
launchctl list | grep veranstaltungen    # Status prüfen
launchctl start de.veranstaltungen-ms.update  # Manuell auslösen
```

## Architektur

**Datenfluss:** API → scraper.py → app.py → HTML-Dateien

- `scraper.py`: API-Client mit `hole_veranstaltungen(jahr, monat)`. POST-Request an `/dpms/` Proxy-Endpoint, paginiert (100 Events/Seite). Laufende Events aus Vormonaten werden auf den 1. des Monats mit Uhrzeit "laufend" gesetzt.
- `app.py`: Ruft Scraper auf, generiert statische HTML-Dashboards pro Monat mit eingebettetem CSS/JS, Monatsnavigation und Stadtfilter.

## Datenquelle

JSON-API via POST an `https://www.muensterland.com/dpms/` (Proxy für Datenportal Münsterland).

Parameter:
- `endpoint=events`
- `page[size]=100`, `page[number]=1`
- `returnFormat=json`
- `from=YYYY-MM-DD`, `to=YYYY-MM-DD`

Response enthält: name, start_datetime, end_datetime, poi (Ort/Adresse), description_text, external_link.
