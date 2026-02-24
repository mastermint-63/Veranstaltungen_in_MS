"""API-Client für Veranstaltungen aus dem Münsterland (muensterland.com + Digital Hub + Halle Münsterland)."""

import re
import json
import requests
from dataclasses import dataclass, field
from datetime import datetime
from calendar import monthrange
from html import unescape
from bs4 import BeautifulSoup


API_URL = "https://www.muensterland.com/dpms/"
PAGE_SIZE = 100

# Digital Hub API
DIGITALHUB_API_URL = "https://www.digitalhub.ms/api/events"
DIGITALHUB_API_KEY = "089d362b33ef053d7fcd241d823d27d1"  # Öffentlicher Demo-Key

# Halle Münsterland
HALLE_MUENSTERLAND_URL = "https://www.mcc-halle-muensterland.de/de/gaeste/veranstaltungen/"

# regioactive — Städte mit City-ID und URL-Slug
REGIOACTIVE_STAEDTE = [
    (21196, 'muenster',  'Münster'),
    (14632, 'bocholt',   'Bocholt'),
    (14777, 'borken',    'Borken'),
    (13413, 'ahaus',     'Ahaus'),
    (17403, 'gronau',    'Gronau'),
]
REGIOACTIVE_URL_TEMPLATE = "https://www.regioactive.de/events/{city_id}/{slug}/veranstaltungen-party-konzerte/monat/{jahr}-{monat:02d}"

# Theater Münster
THEATER_MS_URL = "https://neu.theater-muenster.com/spielplan"

# LWL-Museum für Kunst und Kultur
LWL_MUSEUM_URL = "https://www.lwl-museum-kunst-kultur.de/de/touren-workshops/termine-und-veranstaltungen/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
}


@dataclass
class Veranstaltung:
    """Eine Veranstaltung im Münsterland."""
    name: str
    datum: datetime
    uhrzeit: str
    ort: str
    stadt: str
    link: str
    beschreibung: str = ''
    quelle: str = 'muensterland'  # 'muensterland' oder 'digitalhub'
    kategorie: str = ''  # z.B. 'Workshop', 'Meetup', 'Pitch'

    def datum_formatiert(self) -> str:
        """Formatiert das Datum als 'Mo 02.02.2026'."""
        tage = ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']
        return f"{tage[self.datum.weekday()]} {self.datum.strftime('%d.%m.%Y')}"

    def __lt__(self, other):
        return (self.datum, self.uhrzeit, self.name) < (other.datum, other.uhrzeit, other.name)


def _html_zu_text(html: str) -> str:
    """Konvertiert HTML zu reinem Text."""
    text = re.sub(r'<br\s*/?>', '\n', html)
    text = re.sub(r'<[^>]+>', '', text)
    text = unescape(text)
    return text.strip()


def _parse_event(event: dict) -> Veranstaltung | None:
    """Parst ein einzelnes Event aus der API-Antwort."""
    name = event.get('name', '').strip()
    if not name:
        return None

    # Datum und Uhrzeit
    start_str = event.get('start_datetime', '')
    if not start_str:
        return None

    try:
        # Format: 2026-02-05T16:00:00+01:00
        datum = datetime.fromisoformat(start_str)
    except ValueError:
        return None

    # Uhrzeit: "00:00" bedeutet meist ganztägig
    if datum.hour == 0 and datum.minute == 0:
        uhrzeit = 'ganztägig'
    else:
        uhrzeit = datum.strftime('%H:%M Uhr')

    # Ort und Stadt aus POI
    poi = event.get('poi') or {}
    ort_name = poi.get('name', '')
    adresse = poi.get('address') or {}
    stadt = adresse.get('city', '')

    ort_teile = [ort_name]
    strasse = adresse.get('street', '')
    hausnr = adresse.get('house_number', '')
    if strasse:
        ort_teile.append(f"{strasse} {hausnr}".strip())
    ort = ', '.join(t for t in ort_teile if t)

    # Link: nur external_link verwenden (muensterland.com hat keine Event-Detailseiten)
    link = event.get('external_link') or ''

    # Hinweis für mehrtägige Veranstaltungen
    bis_hinweis = ''
    end_str = event.get('end_datetime', '')
    if end_str:
        try:
            end_datum = datetime.fromisoformat(end_str).replace(tzinfo=None)
            delta = (end_datum.date() - datum.replace(tzinfo=None).date()).days
            if delta > 1:
                bis_hinweis = f"Läuft bis {end_datum.strftime('%d.%m.%Y')}"
        except ValueError:
            pass

    # Beschreibung
    beschreibung_html = event.get('description_text', '')
    beschreibung = _html_zu_text(beschreibung_html)
    if bis_hinweis:
        beschreibung = bis_hinweis + (' · ' + beschreibung[:200] if beschreibung else '')
    elif link:
        beschreibung = beschreibung[:300]

    return Veranstaltung(
        name=name[:150],
        datum=datum.replace(tzinfo=None),
        uhrzeit=uhrzeit,
        ort=ort[:150],
        stadt=stadt,
        link=link,
        beschreibung=beschreibung,
    )


def hole_veranstaltungen(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt alle Veranstaltungen für einen bestimmten Monat."""
    letzter_tag = monthrange(jahr, monat)[1]
    von = f"{jahr}-{monat:02d}-01"
    bis = f"{jahr}-{monat:02d}-{letzter_tag}"

    veranstaltungen = []
    seite = 1

    while True:
        params = {
            'endpoint': 'events',
            'page[size]': str(PAGE_SIZE),
            'page[number]': str(seite),
            'returnFormat': 'json',
            'from': von,
            'to': bis,
        }

        try:
            response = requests.post(API_URL, data=params, headers=HEADERS, timeout=30)
            response.raise_for_status()
            daten = response.json()
        except (requests.RequestException, ValueError) as e:
            print(f"  Fehler beim Abrufen (Seite {seite}): {e}")
            break

        events = daten.get('data', [])
        if not events:
            break

        monats_start = datetime(jahr, monat, 1)
        for event in events:
            v = _parse_event(event)
            if not v:
                continue
            # Nur Events zeigen, die in diesem Monat beginnen (Eröffnungstag)
            if v.datum < monats_start:
                continue
            if v.datum.year == jahr and v.datum.month == monat:
                veranstaltungen.append(v)

        # Wenn weniger als PAGE_SIZE zurückkommen, war es die letzte Seite
        if len(events) < PAGE_SIZE:
            break

        seite += 1

    veranstaltungen.sort()
    return veranstaltungen


def hole_digitalhub_events(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt Digital Hub Events für einen bestimmten Monat."""
    params = {
        'api_token': DIGITALHUB_API_KEY
    }

    try:
        response = requests.get(DIGITALHUB_API_URL, params=params, headers=HEADERS, timeout=30)
        response.raise_for_status()
        daten = response.json()
    except (requests.RequestException, ValueError) as e:
        print(f"  Digital Hub API-Fehler: {e}")
        return []

    # Events sind im "data"-Array
    events = daten.get('data', [])
    if not events:
        return []

    veranstaltungen = []
    monats_start = datetime(jahr, monat, 1)
    letzter_tag = monthrange(jahr, monat)[1]
    monats_ende = datetime(jahr, monat, letzter_tag, 23, 59, 59)

    for event in events:
        # Datum parsen
        start_date = event.get('start_date', '')
        if not start_date:
            continue

        try:
            datum = datetime.strptime(start_date, '%Y-%m-%d')
        except ValueError:
            continue

        # Nur Events im gewünschten Monat
        if datum < monats_start or datum > monats_ende:
            continue

        # Uhrzeit
        start_time = event.get('start_time', '').strip()
        end_time = event.get('end_time', '').strip()
        if start_time:
            uhrzeit = f"{start_time} Uhr"
            if end_time:
                uhrzeit = f"{start_time}-{end_time} Uhr"
            # Datum mit Uhrzeit
            try:
                stunde, minute = map(int, start_time.split(':'))
                datum = datum.replace(hour=stunde, minute=minute)
            except (ValueError, AttributeError):
                pass
        else:
            uhrzeit = 'ganztägig'

        # Ort und Stadt
        address = event.get('address', '')
        stadt = event.get('city', '')

        # Name und Link
        name = event.get('title', '').strip()
        if not name:
            continue

        link = event.get('link_url', '') or f"https://www.digitalhub.ms/events"

        # Beschreibung
        beschreibung = event.get('desc', '').strip()[:300]

        # Kategorie
        mode = event.get('mode', '')
        flag = event.get('flag', '')
        kategorie = f"{mode}" if mode else ''
        if flag:
            kategorie = f"{flag} · {kategorie}" if kategorie else flag

        veranstaltungen.append(Veranstaltung(
            name=name[:150],
            datum=datum,
            uhrzeit=uhrzeit,
            ort=(address or '')[:150],
            stadt=stadt,
            link=link,
            beschreibung=beschreibung,
            quelle='digitalhub',
            kategorie=kategorie
        ))

    return veranstaltungen


def hole_halle_muensterland_events(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt Events von der Halle Münsterland für einen bestimmten Monat."""
    try:
        response = requests.get(HALLE_MUENSTERLAND_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Halle Münsterland Fehler: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    veranstaltungen = []

    # Alle Event-Cards finden
    cards = soup.find_all('div', class_='card', attrs={'data-date': True})

    for card in cards:
        # Datum aus data-Attributen extrahieren
        data_month = card.get('data-month', '')
        data_year = card.get('data-year', '')

        if not data_month or not data_year:
            continue

        # Jahr ist zweistellig (26 = 2026)
        try:
            event_monat = int(data_month)
            event_jahr = 2000 + int(data_year)
        except ValueError:
            continue

        # Nur Events im gewünschten Monat
        if event_jahr != jahr or event_monat != monat:
            continue

        # Tag aus data-date extrahieren (Format: MM-DD-YY)
        data_date = card.get('data-date', '')
        try:
            parts = data_date.split('-')
            tag = int(parts[1]) if len(parts) >= 2 else 1
        except (ValueError, IndexError):
            tag = 1

        datum = datetime(event_jahr, event_monat, tag)

        # Event-Titel aus img title extrahieren
        img = card.find('img', attrs={'title': True})
        if img and img.get('title'):
            name = img['title'].strip()
        else:
            # Fallback: Versuche anderen Text zu finden
            continue

        if not name:
            continue

        # Eventim-Link extrahieren
        eventim_link = card.find('a', href=lambda h: h and 'eventim.de' in h)
        link = eventim_link['href'] if eventim_link else ''

        # End-Datum prüfen (mehrtägige Events)
        data_enddate = card.get('data-enddate', '')
        if data_enddate:
            try:
                end_parts = data_enddate.split('-')
                end_tag = int(end_parts[1])
                uhrzeit = f"{tag:02d}.–{end_tag:02d}.{event_monat:02d}."
            except (ValueError, IndexError):
                uhrzeit = 'siehe Website'
        else:
            uhrzeit = 'siehe Website'

        veranstaltungen.append(Veranstaltung(
            name=name[:150],
            datum=datum,
            uhrzeit=uhrzeit,
            ort='Halle Münsterland',
            stadt='Münster',
            link=link,
            beschreibung='',
            quelle='halle_muensterland',
            kategorie='Konzert/Show'
        ))

    return veranstaltungen


def _hole_regioactive_stadt(city_id: int, slug: str, stadt_name: str,
                             jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt Events von regioactive.de für eine Stadt via JSON-LD."""
    url = REGIOACTIVE_URL_TEMPLATE.format(city_id=city_id, slug=slug, jahr=jahr, monat=monat)
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  regioactive {stadt_name} Fehler: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    veranstaltungen = []

    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
        except (json.JSONDecodeError, TypeError):
            continue

        events = []
        if data.get('@type') == 'ItemList':
            for item in data.get('itemListElement', []):
                ev = item.get('item', {})
                if ev.get('@type') == 'Event':
                    events.append(ev)
        elif data.get('@type') == 'Event':
            events.append(data)

        for event in events:
            name = event.get('name', '').strip()
            if not name:
                continue

            start = event.get('startDate', '')
            if not start:
                continue
            try:
                datum = datetime.fromisoformat(start).replace(tzinfo=None)
            except ValueError:
                continue

            if datum.year != jahr or datum.month != monat:
                continue

            uhrzeit = datum.strftime('%H:%M Uhr') if (datum.hour or datum.minute) else 'ganztägig'

            location = event.get('location', {}) if isinstance(event.get('location'), dict) else {}
            ort = location.get('name', '')
            adresse = location.get('address', {}) if isinstance(location.get('address'), dict) else {}
            if adresse.get('streetAddress') and ort:
                ort = f"{ort}, {adresse['streetAddress']}"

            link = event.get('url', '')
            beschreibung = _html_zu_text(event.get('description', ''))[:300]

            veranstaltungen.append(Veranstaltung(
                name=name[:150],
                datum=datum,
                uhrzeit=uhrzeit,
                ort=ort[:150],
                stadt=stadt_name,
                link=link,
                beschreibung=beschreibung,
                quelle='regioactive',
            ))

    return veranstaltungen


def hole_regioactive_ms(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt Events von regioactive.de für Münster + Kreis-Borken-Städte."""
    veranstaltungen = []
    for city_id, slug, stadt_name in REGIOACTIVE_STAEDTE:
        veranstaltungen.extend(_hole_regioactive_stadt(city_id, slug, stadt_name, jahr, monat))
    return veranstaltungen


def hole_theater_muenster(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt den Spielplan des Theater Münster via HTML-Scraping."""
    url = f"{THEATER_MS_URL}?date={jahr:04d}-{monat:02d}"
    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"  Theater Münster Fehler: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    veranstaltungen = []

    for perf in soup.find_all('div', class_='tm-performance'):
        # Tag aus dayNumber (kann Anker-Tags enthalten)
        day_elem = perf.find('div', class_='tm-performance__dayNumber')
        if not day_elem:
            continue
        m = re.search(r'\d+', day_elem.get_text())
        if not m:
            continue
        tag = int(m.group())
        if not 1 <= tag <= 31:
            continue

        # Uhrzeit: "16.30 Uhr" → "16:30 Uhr"
        time_elem = perf.find('div', class_='tm-performance__performanceTime')
        uhrzeit_raw = time_elem.get_text(strip=True) if time_elem else ''
        uhrzeit = re.sub(r'(\d{1,2})\.(\d{2})\s*Uhr', r'\1:\2 Uhr', uhrzeit_raw) if uhrzeit_raw else 'siehe Website'

        # Ort / Bühne
        loc_elem = perf.find('div', class_='tm-performance__location')
        ort = loc_elem.get_text(strip=True) if loc_elem else 'Theater Münster'

        # Titel + Link
        prod_div = perf.find('div', class_='tm-performance__productionName')
        if not prod_div:
            continue
        link_elem = prod_div.find('a')
        if not link_elem:
            continue
        name = link_elem.get_text(strip=True)
        href = link_elem.get('href', '')
        link = f"https://neu.theater-muenster.com{href}" if href.startswith('/') else href

        if not name:
            continue

        # Kategorie
        cat_elem = perf.find('li', class_='tm-performance__category')
        kategorie = cat_elem.get_text(strip=True) if cat_elem else ''

        # Kurzbeschreibung
        info_elem = perf.find('div', class_='tm-performance__productionInfo')
        beschreibung = info_elem.get_text(strip=True) if info_elem else ''

        try:
            datum = datetime(jahr, monat, tag)
        except ValueError:
            continue

        veranstaltungen.append(Veranstaltung(
            name=name[:150],
            datum=datum,
            uhrzeit=uhrzeit,
            ort=ort[:150],
            stadt='Münster',
            link=link,
            beschreibung=beschreibung[:200],
            quelle='theater_muenster',
            kategorie=kategorie,
        ))

    return veranstaltungen


def hole_lwl_museum(jahr: int, monat: int) -> list[Veranstaltung]:
    """Holt Veranstaltungen vom LWL-Museum für Kunst und Kultur via HTML-Scraping."""
    letzter_tag = monthrange(jahr, monat)[1]
    von = f"01.{monat:02d}.{jahr}"
    bis = f"{letzter_tag:02d}.{monat:02d}.{jahr}"

    veranstaltungen = []
    MAX_SEITEN = 10

    for seite in range(1, MAX_SEITEN + 1):
        url = f"{LWL_MUSEUM_URL}?vom={von}&bis={bis}&p={seite}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"  LWL Museum Fehler (Seite {seite}): {e}")
            break

        soup = BeautifulSoup(response.text, 'html.parser')
        event_elems = soup.find_all('div', class_='event-element')
        if not event_elems:
            break

        for elem in event_elems:
            # Datum: "Dienstag, 24.2.2026" → datetime
            date_p = elem.find('p', class_='event-date')
            if not date_p:
                continue
            date_text = date_p.get_text(strip=True)
            date_part = date_text.split(',', 1)[1].strip() if ',' in date_text else date_text
            try:
                parts = [p.strip() for p in date_part.split('.')]
                datum = datetime(int(parts[2]), int(parts[1]), int(parts[0]))
            except (ValueError, IndexError):
                continue

            if datum.year != jahr or datum.month != monat:
                continue

            # Uhrzeit: "10.30 - 12.30 Uhr" → "10:30 - 12:30 Uhr"
            time_p = elem.find('p', class_='event-time')
            uhrzeit_raw = time_p.get_text(strip=True) if time_p else 'siehe Website'
            uhrzeit = re.sub(r'(\d{1,2})\.(\d{2})', r'\1:\2', uhrzeit_raw)

            # Titel: <h4 class="event-title"><span id="event-title-XXXXX">
            title_h4 = elem.find('h4', class_='event-title')
            if not title_h4:
                continue
            title_span = title_h4.find('span', id=re.compile(r'^event-title-'))
            if not title_span:
                continue
            name = title_span.get_text(strip=True)
            event_id = title_span.get('id', '').replace('event-title-', '')
            link = f"https://www.lwl-museum-kunst-kultur.de/de/touren-workshops/termine-und-veranstaltungen/?id={event_id}" if event_id else ''

            if not name:
                continue

            # Beschreibung
            desc_p = elem.find('p', class_='event-description')
            beschreibung = desc_p.get_text(strip=True) if desc_p else ''

            # Kategorie (Zielgruppe)
            type_p = elem.find('p', class_='event-type')
            kategorie = type_p.get_text(strip=True) if type_p else ''

            veranstaltungen.append(Veranstaltung(
                name=name[:150],
                datum=datum,
                uhrzeit=uhrzeit,
                ort='LWL-Museum für Kunst und Kultur',
                stadt='Münster',
                link=link,
                beschreibung=beschreibung[:200],
                quelle='lwl_museum',
                kategorie=kategorie,
            ))

        # Gibt es eine nächste Seite?
        pagination = soup.find('ul', class_='pagination')
        if not pagination:
            break
        # Suche nach aktivem Element und ob danach noch eines folgt
        items = pagination.find_all('li')
        aktiv_idx = next((i for i, li in enumerate(items) if 'active' in li.get('class', [])), None)
        if aktiv_idx is None or aktiv_idx >= len(items) - 2:  # letztes li ist meist "›"
            break
        # Prüfe ob "next"-Link tatsächlich eine Seite verlinkt
        next_li = items[aktiv_idx + 1] if aktiv_idx + 1 < len(items) else None
        if not next_li or not next_li.find('a', href=True):
            break

    return veranstaltungen
