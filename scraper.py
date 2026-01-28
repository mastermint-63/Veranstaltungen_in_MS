"""API-Client für Veranstaltungen aus dem Münsterland (muensterland.com)."""

import re
import requests
from dataclasses import dataclass, field
from datetime import datetime
from calendar import monthrange
from html import unescape


API_URL = "https://www.muensterland.com/dpms/"
PAGE_SIZE = 100

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

    # Link: external_link oder muensterland.com Event-Seite
    link = event.get('external_link') or ''
    if not link:
        event_id = event.get('id')
        if event_id:
            link = f"https://www.muensterland.com/tourismus/service/veranstaltungen-im-muensterland/?id={event_id}"

    # Beschreibung
    beschreibung_html = event.get('description_text', '')
    beschreibung = _html_zu_text(beschreibung_html)[:300]

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
            # Laufende Events aus Vormonaten: Datum auf Monatsanfang setzen
            if v.datum < monats_start:
                v.datum = monats_start
                v.uhrzeit = 'laufend'
            if v.datum.year == jahr and v.datum.month == monat:
                veranstaltungen.append(v)

        # Wenn weniger als PAGE_SIZE zurückkommen, war es die letzte Seite
        if len(events) < PAGE_SIZE:
            break

        seite += 1

    veranstaltungen.sort()
    return veranstaltungen
