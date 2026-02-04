# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektbeschreibung

Veranstaltungs-Dashboard für das Münsterland. Sammelt Events von drei Quellen:
- **muensterland.com** (Datenportal-API): Allgemeine Veranstaltungen
- **Digital Hub münsterLAND** (digitalhub.ms API): Startup- und Tech-Events
- **Halle Münsterland** (HTML-Scraping): Konzerte, Shows, Messen

Generiert statische HTML-Dashboards mit Kalender, Filtern und Dark Mode.

## Ausführung

```bash
python3 app.py                    # 3 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 3 Monate ab Feb 2026
python3 app.py 2026 1 12          # 12 Monate (ganzes Jahr)
python3 app.py --no-browser       # Ohne Browser öffnen

./update.sh                       # Aktualisieren + Git Push + macOS-Benachrichtigung
./oeffne_aktuell.sh               # Aktuellen Monat im Browser öffnen
```

## GitHub Pages Deployment

- **Repository:** https://github.com/mastermint-63/Veranstaltungen_in_MS
- **Pages URL:** https://mastermint-63.github.io/Veranstaltungen_in_MS/
- **Custom Domain (geplant):** ms-veranstaltungen.reporter.ruhr

**Workflow:** `update.sh` scrapt → generiert HTML → pusht zu GitHub → Actions deployt automatisch

```bash
gh run list --workflow=deploy.yml    # Deployment-Status prüfen
```

## Automatische Aktualisierung (launchd)

Läuft täglich um 6:15 Uhr:
- Plist: `~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist`
- Log: `launchd.log`

```bash
launchctl list | grep veranstaltungen      # Status prüfen
launchctl start de.veranstaltungen-ms.update   # Manuell auslösen
tail -f launchd.log                        # Live-Log anzeigen
```

## Architektur

```
API-Quellen → scraper.py → app.py → HTML-Dateien → GitHub Pages
```

### scraper.py

Enthält `Veranstaltung`-Dataclass und API-Clients:

| Funktion | Quelle | Methode |
|----------|--------|---------|
| `hole_veranstaltungen(jahr, monat)` | muensterland.com | POST, paginiert (100/Seite) |
| `hole_digitalhub_events(jahr, monat)` | digitalhub.ms | GET mit API-Token |
| `hole_halle_muensterland_events(jahr, monat)` | mcc-halle-muensterland.de | HTML-Scraping (BeautifulSoup) |

Beide geben `list[Veranstaltung]` zurück.

### app.py

- Ruft beide Scraper-Funktionen auf
- Kombiniert Events mit `.extend()`
- Generiert standalone HTML (eingebettetes CSS/JS)
- Dateinamen: `veranstaltungen_YYYY_MM.html`

### update.sh

- Scrapt Events, generiert HTML
- Git add/commit/push bei Änderungen
- macOS-Notification mit Event-Statistik

## Neue Datenquelle hinzufügen

1. **Funktion in `scraper.py`** erstellen:
   ```python
   def hole_neue_quelle(jahr: int, monat: int) -> list[Veranstaltung]:
       # Events abrufen, Veranstaltung-Objekte zurückgeben
       pass
   ```

2. **In `app.py`** importieren und aufrufen:
   ```python
   from scraper import hole_neue_quelle
   # In main():
   neue_events = hole_neue_quelle(j, m)
   veranstaltungen.extend(neue_events)
   ```

3. **`quelle`-Parameter** setzen für Filter-Dropdown

## API-Dokumentation

### Münsterland Events

POST `https://www.muensterland.com/dpms/`
```
endpoint=events
page[size]=100
page[number]=1
from=YYYY-MM-DD
to=YYYY-MM-DD
returnFormat=json
```

### Digital Hub

GET `https://www.digitalhub.ms/api/events?api_token=089d362b33ef053d7fcd241d823d27d1`

Dokumentation: https://www.digitalhub.ms/api

## Fehlerbehandlung

- API-Timeout: 30s, Fehler wird geloggt, andere Quellen laufen weiter
- `update.sh` erkennt Fehler und sendet Warn-Notification (⚠️ mit Basso-Sound)
