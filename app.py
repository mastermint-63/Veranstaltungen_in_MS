#!/usr/bin/env python3
"""
Veranstaltungen im Münsterland — Dashboard
Sammelt Veranstaltungen von muensterland.com und generiert ein HTML-Dashboard.

Verwendung:
    python3 app.py              # Generiert aktuellen + 2 weitere Monate
    python3 app.py 2026 2       # Generiert ab Februar 2026 (3 Monate)
    python3 app.py 2026 2 6     # Generiert 6 Monate ab Februar 2026
    python3 app.py --no-browser # Ohne Browser öffnen
"""

import os
import webbrowser
import calendar
from datetime import datetime

from scraper import hole_veranstaltungen, hole_digitalhub_events, Veranstaltung


def dateiname_fuer_monat(jahr: int, monat: int) -> str:
    """Generiert den Dateinamen für einen Monat."""
    return f"veranstaltungen_{jahr}_{monat:02d}.html"


def generiere_kalender(jahr: int, monat: int, tage_mit_events: set[int]) -> str:
    """Generiert ein Kalenderblatt als HTML-Tabelle."""
    cal = calendar.Calendar(firstweekday=0)  # Montag = 0
    wochen = cal.monthdayscalendar(jahr, monat)

    html = '<table class="kalender" id="kalender">\n'
    html += '<tr>'
    for tag_name in ['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So']:
        html += f'<th>{tag_name}</th>'
    html += '</tr>\n'

    for woche in wochen:
        html += '<tr>'
        for tag in woche:
            if tag == 0:
                html += '<td></td>'
            elif tag in tage_mit_events:
                datum_key = f"{jahr}-{monat:02d}-{tag:02d}"
                html += f'<td><a href="#datum-{datum_key}" class="kal-link">{tag}</a></td>'
            else:
                html += f'<td class="kal-leer">{tag}</td>'
        html += '</tr>\n'

    html += '</table>'
    return html


def generiere_html(veranstaltungen: list[Veranstaltung], jahr: int, monat: int,
                   verfuegbare_monate: list[tuple[int, int]]) -> str:
    """Generiert das HTML-Dashboard."""
    monatsnamen = [
        '', 'Januar', 'Februar', 'März', 'April', 'Mai', 'Juni',
        'Juli', 'August', 'September', 'Oktober', 'November', 'Dezember'
    ]

    # Termine nach Datum gruppieren
    nach_datum = {}
    for v in veranstaltungen:
        key = v.datum.strftime('%Y-%m-%d')
        if key not in nach_datum:
            nach_datum[key] = []
        nach_datum[key].append(v)

    # Alle Städte für Filter
    alle_staedte = sorted(set(v.stadt for v in veranstaltungen if v.stadt))

    # Termine-HTML
    termine_html = ""
    for datum_key in sorted(nach_datum.keys()):
        tage = nach_datum[datum_key]
        datum_formatiert = tage[0].datum_formatiert()

        termine_html += f'''
        <div class="datum-gruppe" id="datum-{datum_key}">
            <div class="datum-header">{datum_formatiert}</div>
            <div class="termine-liste">
        '''

        for v in sorted(tage, key=lambda x: (x.uhrzeit == 'ganztägig', x.uhrzeit, x.name)):
            beschreibung_raw = v.beschreibung.replace('"', '&quot;').replace('\n', ' ')
            beschreibung_escaped = beschreibung_raw[:200] if v.link else beschreibung_raw

            # Badge für Digital Hub Events
            badge_html = ''
            if v.quelle == 'digitalhub':
                badge_html = '<span class="badge badge-digitalhub">🚀 Digital Hub</span>'
                if v.kategorie:
                    badge_html += f' <span class="badge badge-kategorie">{v.kategorie}</span>'

            # Name: als Link oder aufklappbar
            if v.link:
                name_html = f'<a href="{v.link}" target="_blank">{v.name}</a>'
            else:
                name_html = f'<span class="termin-toggle" onclick="this.closest(\'.termin\').classList.toggle(\'expanded\')">{v.name}</span>'

            termine_html += f'''
                <div class="termin" data-stadt="{v.stadt}" data-quelle="{v.quelle}">
                    <div class="termin-zeit">{v.uhrzeit}</div>
                    <div class="termin-info">
                        <div class="termin-name">
                            {name_html}
                            {badge_html}
                        </div>
                        <div class="termin-stadt">{v.stadt}</div>
                        {f'<div class="termin-ort">{v.ort}</div>' if v.ort else ''}
                        {f'<div class="termin-beschreibung">{beschreibung_escaped}</div>' if beschreibung_escaped else ''}
                    </div>
                </div>
            '''

        termine_html += '''
            </div>
            <div class="zurueck-link"><a href="#kalender">↑ Kalender</a></div>
        </div>
        '''

    # Filter-Optionen
    filter_html = '<option value="">Alle Städte</option>'
    for stadt in alle_staedte:
        filter_html += f'<option value="{stadt}">{stadt}</option>'

    # Monatsnavigation
    prev_monat = monat - 1 if monat > 1 else 12
    prev_jahr = jahr if monat > 1 else jahr - 1
    next_monat = monat + 1 if monat < 12 else 1
    next_jahr = jahr if monat < 12 else jahr + 1

    prev_verfuegbar = (prev_jahr, prev_monat) in verfuegbare_monate
    next_verfuegbar = (next_jahr, next_monat) in verfuegbare_monate

    prev_link = dateiname_fuer_monat(prev_jahr, prev_monat) if prev_verfuegbar else "#"
    next_link = dateiname_fuer_monat(next_jahr, next_monat) if next_verfuegbar else "#"

    prev_class = "" if prev_verfuegbar else " disabled"
    next_class = "" if next_verfuegbar else " disabled"

    # Kalenderblatt generieren
    tage_mit_events = set(int(k.split('-')[2]) for k in nach_datum.keys())
    kalender_html = generiere_kalender(jahr, monat, tage_mit_events)

    html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Veranstaltungen Münsterland — {monatsnamen[monat]} {jahr}</title>
    <style>
        :root {{
            --bg-color: #f5f5f7;
            --card-bg: #ffffff;
            --text-color: #1d1d1f;
            --text-secondary: #86868b;
            --border-color: #d2d2d7;
            --accent-color: #347c3b;
            --hover-color: #f0f0f5;
        }}

        @media (prefers-color-scheme: dark) {{
            :root {{
                --bg-color: #1d1d1f;
                --card-bg: #2d2d2f;
                --text-color: #f5f5f7;
                --text-secondary: #a1a1a6;
                --border-color: #424245;
                --accent-color: #5cb85c;
                --hover-color: #3a3a3c;
            }}
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: var(--bg-color);
            color: var(--text-color);
            line-height: 1.5;
            padding: 20px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        header {{
            text-align: center;
            margin-bottom: 30px;
        }}

        h1 {{
            font-size: 2rem;
            font-weight: 600;
            margin-bottom: 10px;
        }}

        .nav {{
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 20px;
            margin-bottom: 20px;
        }}

        .nav-btn {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--accent-color);
            padding: 8px 16px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            text-decoration: none;
        }}

        .nav-btn:hover {{
            background: var(--hover-color);
        }}

        .nav-btn.disabled {{
            opacity: 0.3;
            pointer-events: none;
            cursor: default;
        }}

        .monat-titel {{
            font-size: 1.2rem;
            font-weight: 500;
        }}

        .filter-bar {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 10px 15px;
            background: var(--card-bg);
            border-radius: 10px;
            border: 1px solid var(--border-color);
            flex-wrap: wrap;
            gap: 10px;
        }}

        .filter-group {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}

        .filter-bar select {{
            padding: 8px 12px;
            border: 1px solid var(--border-color);
            border-radius: 6px;
            background: var(--bg-color);
            color: var(--text-color);
            font-size: 14px;
        }}

        .stats {{
            font-size: 14px;
            color: var(--text-secondary);
        }}

        .datum-gruppe {{
            margin-bottom: 20px;
        }}

        .datum-header {{
            font-weight: 600;
            font-size: 1rem;
            padding: 10px 15px;
            background: var(--accent-color);
            color: white;
            border-radius: 10px 10px 0 0;
        }}

        .termine-liste {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-top: none;
            border-radius: 0 0 10px 10px;
        }}

        .termin {{
            display: flex;
            padding: 12px 15px;
            border-bottom: 1px solid var(--border-color);
            transition: background 0.2s;
        }}

        .termin:last-child {{
            border-bottom: none;
        }}

        .termin:hover {{
            background: var(--hover-color);
        }}

        .termin-zeit {{
            width: 90px;
            font-weight: 500;
            color: var(--accent-color);
            flex-shrink: 0;
        }}

        .termin-info {{
            flex: 1;
        }}

        .termin-name {{
            font-weight: 500;
            margin-bottom: 2px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}

        .termin-name a {{
            color: var(--text-color);
            text-decoration: none;
        }}

        .termin-name a:hover {{
            color: var(--accent-color);
            text-decoration: underline;
        }}

        .badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 500;
            white-space: nowrap;
        }}

        .badge-digitalhub {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        .badge-kategorie {{
            background: var(--hover-color);
            color: var(--text-secondary);
            border: 1px solid var(--border-color);
        }}

        .termin-stadt {{
            font-size: 13px;
            color: var(--text-secondary);
        }}

        .termin-ort {{
            font-size: 12px;
            color: var(--text-secondary);
            font-style: italic;
        }}

        .termin-beschreibung {{
            font-size: 12px;
            color: var(--text-secondary);
            margin-top: 4px;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}

        .termin-toggle {{
            cursor: pointer;
            color: var(--text-color);
            border-bottom: 1px dashed var(--text-secondary);
        }}

        .termin-toggle:hover {{
            color: var(--accent-color);
        }}

        .termin-toggle::after {{
            content: ' ▸';
            font-size: 11px;
            color: var(--text-secondary);
        }}

        .termin.expanded .termin-toggle::after {{
            content: ' ▾';
        }}

        .termin:has(.termin-toggle) .termin-beschreibung {{
            display: none;
        }}

        .termin.expanded .termin-beschreibung {{
            display: block;
            -webkit-line-clamp: unset;
            overflow: visible;
        }}

        .zurueck-link {{
            text-align: right;
            padding: 6px 15px;
            font-size: 13px;
        }}

        .zurueck-link a {{
            color: var(--accent-color);
            text-decoration: none;
            font-weight: 500;
        }}

        .zurueck-link a:hover {{
            color: var(--accent-color);
        }}

        .keine-termine {{
            text-align: center;
            padding: 40px;
            color: var(--text-secondary);
        }}

        .hidden {{
            display: none !important;
        }}

        footer {{
            text-align: center;
            margin-top: 30px;
            padding: 20px;
            color: var(--text-secondary);
            font-size: 12px;
        }}

        footer a {{
            color: var(--text-secondary);
        }}

        .kalender {{
            width: 100%;
            max-width: 400px;
            margin: 0 auto 25px;
            border-collapse: collapse;
            text-align: center;
        }}

        .kalender th {{
            padding: 6px;
            font-size: 13px;
            color: var(--text-secondary);
            font-weight: 500;
        }}

        .kalender td {{
            padding: 6px;
            font-size: 14px;
            border-radius: 6px;
        }}

        .kalender .kal-leer {{
            color: var(--text-secondary);
            opacity: 0.5;
        }}

        .kalender .kal-link {{
            display: inline-block;
            width: 32px;
            height: 32px;
            line-height: 32px;
            border-radius: 50%;
            background: var(--accent-color);
            color: white;
            text-decoration: none;
            font-weight: 600;
        }}

        .kalender .kal-link:hover {{
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Veranstaltungen Münsterland</h1>
            <div class="nav">
                <a href="{prev_link}" class="nav-btn{prev_class}">&larr; {monatsnamen[prev_monat]}</a>
                <span class="monat-titel">{monatsnamen[monat]} {jahr}</span>
                <a href="{next_link}" class="nav-btn{next_class}">{monatsnamen[next_monat]} &rarr;</a>
            </div>
        </header>

        {kalender_html}

        <div class="filter-bar">
            <div class="filter-group">
                <select id="stadt-filter" onchange="filterTermine()">
                    {filter_html}
                </select>
                <select id="quelle-filter" onchange="filterTermine()">
                    <option value="">Alle Quellen</option>
                    <option value="muensterland">Münsterland</option>
                    <option value="digitalhub">Digital Hub</option>
                </select>
            </div>
            <div class="stats">
                <span id="termine-count">{len(veranstaltungen)}</span> Veranstaltungen in <span id="staedte-count">{len(alle_staedte)}</span> Orten
            </div>
        </div>

        <main id="termine-container">
            {termine_html if veranstaltungen else '<div class="keine-termine">Keine Veranstaltungen gefunden</div>'}
        </main>

        <footer>
            Generiert am {datetime.now().strftime('%d.%m.%Y um %H:%M Uhr')}<br>
            Datenquelle: <a href="https://www.muensterland.com/tourismus/service/veranstaltungen-im-muensterland/" target="_blank">muensterland.com</a>
        </footer>
    </div>

    <script>
        function filterTermine() {{
            const stadtFilter = document.getElementById('stadt-filter').value;
            const quelleFilter = document.getElementById('quelle-filter').value;
            const termine = document.querySelectorAll('.termin');
            let sichtbar = 0;

            termine.forEach(t => {{
                const stadtMatch = !stadtFilter || t.dataset.stadt === stadtFilter;
                const quelleMatch = !quelleFilter || t.dataset.quelle === quelleFilter;

                if (stadtMatch && quelleMatch) {{
                    t.classList.remove('hidden');
                    sichtbar++;
                }} else {{
                    t.classList.add('hidden');
                }}
            }});

            document.getElementById('termine-count').textContent = sichtbar;

            document.querySelectorAll('.datum-gruppe').forEach(g => {{
                const sichtbareTermine = g.querySelectorAll('.termin:not(.hidden)');
                g.classList.toggle('hidden', sichtbareTermine.length === 0);
            }});
        }}
    </script>
</body>
</html>'''

    return html


def berechne_monate(start_jahr: int, start_monat: int, anzahl: int) -> list[tuple[int, int]]:
    """Berechnet eine Liste von (jahr, monat) Tupeln."""
    monate = []
    jahr, monat = start_jahr, start_monat
    for _ in range(anzahl):
        monate.append((jahr, monat))
        monat += 1
        if monat > 12:
            monat = 1
            jahr += 1
    return monate


def main():
    """Hauptfunktion."""
    import sys

    no_browser = '--no-browser' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]

    jetzt = datetime.now()
    jahr = int(args[0]) if len(args) > 0 else jetzt.year
    monat = int(args[1]) if len(args) > 1 else jetzt.month
    anzahl_monate = int(args[2]) if len(args) > 2 else 3

    monate_liste = berechne_monate(jahr, monat, anzahl_monate)

    print(f"Generiere {anzahl_monate} Monate ab {monat}/{jahr}...")
    print("=" * 50)

    basis_pfad = os.path.dirname(__file__)
    erster_dateiname = None

    for idx, (j, m) in enumerate(monate_liste):
        monatsnamen = ['', 'Jan', 'Feb', 'Mär', 'Apr', 'Mai', 'Jun',
                       'Jul', 'Aug', 'Sep', 'Okt', 'Nov', 'Dez']
        print(f"\n[{idx+1}/{anzahl_monate}] {monatsnamen[m]} {j}:")

        # Münsterland Events
        veranstaltungen = hole_veranstaltungen(j, m)
        print(f"  → {len(veranstaltungen)} Veranstaltungen von muensterland.com")

        # Digital Hub Events
        digitalhub_events = hole_digitalhub_events(j, m)
        if digitalhub_events:
            print(f"  → {len(digitalhub_events)} Digital Hub Events")
            veranstaltungen.extend(digitalhub_events)

        staedte = len(set(v.stadt for v in veranstaltungen if v.stadt))
        print(f"  → Gesamt: {len(veranstaltungen)} Veranstaltungen in {staedte} Orten")

        html = generiere_html(veranstaltungen, j, m, monate_liste)

        dateiname = dateiname_fuer_monat(j, m)
        ausgabe_pfad = os.path.join(basis_pfad, dateiname)
        with open(ausgabe_pfad, 'w', encoding='utf-8') as f:
            f.write(html)

        if idx == 0:
            erster_dateiname = ausgabe_pfad

    print("\n" + "=" * 50)
    print(f"Fertig! {anzahl_monate} Dateien generiert.")

    if erster_dateiname and not no_browser:
        webbrowser.open(f'file://{erster_dateiname}')


if __name__ == '__main__':
    main()
