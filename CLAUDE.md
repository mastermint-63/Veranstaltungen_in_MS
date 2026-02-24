# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projektbeschreibung

Veranstaltungs-Dashboard für das Münsterland (WDR Studio Münster). Sammelt Events von 6 Quellen und generiert statische HTML-Dashboards mit Kalender, Filtern und Dark Mode.

| Quelle | Typ | Events/Monat | Schwerpunkt |
|--------|-----|-------------|-------------|
| muensterland.com | POST-API, paginiert | ~500 | Allgemeine Veranstaltungen Münsterland |
| Digital Hub münsterLAND | REST-API (GET) | ~2–5 | Startup- und Tech-Events |
| Halle Münsterland | HTML-Scraping | ~8–10 | Konzerte, Shows, Messen |
| regioactive.de | JSON-LD, `/monat/YYYY-MM` | ~40–50 | Konzerte, Partys, Clubs Münster |
| Theater Münster | HTML-Scraping, `?date=YYYY-MM` | ~20–30 | Spielplan Stadttheater |
| LWL-Museum | HTML-Scraping, `?vom=&bis=` | ~60–70 | Touren, Workshops, Events |

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
- **Live URL:** https://ms-veranstaltungen.reporter.ruhr/

**Workflow:** `update.sh` scrapt → generiert HTML → pusht zu GitHub → Actions deployt automatisch

```bash
gh run list --workflow=deploy.yml    # Deployment-Status prüfen
```

## Automatische Aktualisierung

**muensterland.com verwendet Geo-Blocking** (deutsche IP erforderlich) → Scraping läuft lokal via launchd.

```
06:15 Uhr: launchd → update.sh → Scraping (alle 6 Quellen) → HTML → git push → GitHub Pages
```

**Gesamtdauer:** ~30 Sekunden

- Plist: `~/Library/LaunchAgents/de.veranstaltungen-ms.update.plist`
- Log: `launchd.log`

```bash
launchctl list | grep veranstaltungen          # Status prüfen
launchctl start de.veranstaltungen-ms.update   # Manuell auslösen
tail -f launchd.log                            # Live-Log anzeigen
```

## Architektur

```
6 Quellen → scraper.py (Veranstaltung-Objekte) → app.py (HTML-Generierung) → GitHub Pages
```

### scraper.py

Enthält `Veranstaltung`-Dataclass und alle Scraper-Funktionen:

| Funktion | Quelle | Methode |
|----------|--------|---------|
| `hole_veranstaltungen(jahr, monat)` | muensterland.com | POST, paginiert (100/Seite), `end_datetime` für "Läuft bis"-Hinweis |
| `hole_digitalhub_events(jahr, monat)` | digitalhub.ms | GET mit API-Token |
| `hole_halle_muensterland_events(jahr, monat)` | mcc-halle-muensterland.de | HTML, `div.card[data-date]` |
| `hole_regioactive_ms(jahr, monat)` | regioactive.de (City-ID 21196) | JSON-LD Events, `/monat/YYYY-MM` |
| `hole_theater_muenster(jahr, monat)` | neu.theater-muenster.com | HTML, `div.tm-performance`, `?date=YYYY-MM` |
| `hole_lwl_museum(jahr, monat)` | lwl-museum-kunst-kultur.de | HTML, `div.event-element`, `?vom=&bis=`, paginiert |

**Wichtige Regel (muensterland.com):** Nur Events zeigen, die im abgefragten Monat *beginnen* — keine "laufend"-Einträge für Ausstellungen aus Vormonaten. Events mit `end_datetime > start + 1 Tag` bekommen automatisch "Läuft bis DD.MM.YYYY" in die Beschreibung.

### app.py

- `QUELLEN`-Dict: Mapping quelle-Key → Anzeigename
- `BADGE_CONFIG`-Dict: Mapping quelle-Key → (CSS-Klasse, Label)
- `entferne_duplikate()`: Score-basierte Deduplizierung (gleicher Name + gleicher Tag → besseren Eintrag behalten). Score: Link +2, Uhrzeit +2, Beschreibung +1, Ort +1
- Sticky Filter-Bar mit `backdrop-filter: blur` (Milchglas-Effekt)
- Auto-Scroll beim Laden zum ersten heutigen/zukünftigen Termin
- Heute-Markierung im Kalender (`kal-heute`-Klasse)
- Dynamischer Quellen-Filter (nur vorhandene Quellen)
- Städte-Count aktualisiert sich live beim Filtern
- Dateinamen: `veranstaltungen_YYYY_MM.html`

### update.sh

- Scrapt Events, generiert HTML
- Git add/commit/push bei Änderungen
- macOS-Notification mit Event-Statistik

## Neue Datenquelle hinzufügen

1. **Funktion in `scraper.py`** erstellen: `hole_neue_quelle(jahr, monat) -> list[Veranstaltung]`
2. **URL-Konstante** oben in `scraper.py` eintragen
3. **In `app.py`** importieren, `QUELLEN`-Dict ergänzen, `BADGE_CONFIG`-Dict ergänzen
4. **Badge-CSS** in `generiere_html()` ergänzen (`.badge-neuequelle`)
5. **In `main()`** aufrufen und Ergebnis mit `extend()` anhängen
6. **Footer-Link** in `generiere_html()` ergänzen

## API-Dokumentation

### muensterland.com

POST `https://www.muensterland.com/dpms/`
```
endpoint=events
page[size]=100
page[number]=1
from=YYYY-MM-DD
to=YYYY-MM-DD
returnFormat=json
```
Felder: `name`, `start_datetime`, `end_datetime`, `end_datetime_is_approximately`, `description_text`, `external_link`, `poi.name`, `poi.address.city`, `poi.address.street`

### Digital Hub

GET `https://www.digitalhub.ms/api/events?api_token=089d362b33ef053d7fcd241d823d27d1`

### regioactive.de

GET `https://www.regioactive.de/events/21196/muenster/veranstaltungen-party-konzerte/monat/YYYY-MM`
JSON-LD `@type: Event` in `<script>`-Tags, auch als `ItemList` möglich — beide Formate werden unterstützt.

### Theater Münster

GET `https://neu.theater-muenster.com/spielplan?date=YYYY-MM`
CSS-Klassen: `tm-performance__dayNumber`, `tm-performance__performanceTime`, `tm-performance__location`, `tm-performance__productionName`, `tm-performance__category`
Uhrzeit-Format: "16.30 Uhr" → wird zu "16:30 Uhr" normalisiert.

### LWL-Museum

GET `https://www.lwl-museum-kunst-kultur.de/de/touren-workshops/termine-und-veranstaltungen/?vom=DD.MM.YYYY&bis=DD.MM.YYYY&p=N`
CSS-Klassen: `div.event-element`, `p.event-date` ("Dienstag, 24.2.2026"), `p.event-time`, `h4.event-title span[id^="event-title-"]`, `p.event-type`, `p.event-description`
Paginierung: `?p=N`, Abbruch wenn keine weiteren Events.

## Fehlerbehandlung

- Alle Scraper: Timeout 30s, Fehler wird geloggt, andere Quellen laufen weiter
- `update.sh` erkennt Fehler und sendet Warn-Notification (⚠️ mit Basso-Sound)

## Bekannte Einschränkungen

- **muensterland.com Geo-Blocking:** Deutsche IP erforderlich (GitHub Actions liefern 0 Events)
- **Halle Münsterland URL:** `/veranstaltungen` → HTTP 404, Scraper funktioniert trotzdem
- **Theater Münster:** Neue URL `neu.theater-muenster.com` (nicht `theater-muenster.com`)
- **SC Preußen Münster:** Spielplan nicht scrapbar (Website blockiert Requests)
