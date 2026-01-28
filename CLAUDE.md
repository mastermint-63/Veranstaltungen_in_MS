# CLAUDE.md

## Projektbeschreibung

Veranstaltungs-Dashboard für das Münsterland. Sammelt Events von muensterland.com (Datenportal-API) und generiert verlinkte HTML-Dashboards mit Monatsnavigation.

## Struktur

```
├── app.py                          # Hauptanwendung: API-Abruf + HTML-Generator
├── scraper.py                      # API-Client für muensterland.com/dpms/
└── veranstaltungen_YYYY_MM.html    # Generierte Dashboards (pro Monat)
```

## Ausführung

```bash
python3 app.py                    # 3 Monate ab heute, öffnet Browser
python3 app.py 2026 2             # 3 Monate ab Feb 2026
python3 app.py 2026 1 12          # 12 Monate (ganzes Jahr)
python3 app.py --no-browser       # Ohne Browser öffnen
```

## Datenquelle

JSON-API via POST an `https://www.muensterland.com/dpms/` (Proxy für Datenportal Münsterland).
Liefert Veranstaltungsname, Datum/Uhrzeit, Ort mit Adresse, Beschreibung und Links.
