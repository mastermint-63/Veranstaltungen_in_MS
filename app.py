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
from datetime import datetime

from scraper import hole_veranstaltungen, Veranstaltung


def dateiname_fuer_monat(jahr: int, monat: int) -> str:
    """Generiert den Dateinamen für einen Monat."""
    return f"veranstaltungen_{jahr}_{monat:02d}.html"


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
        <div class="datum-gruppe">
            <div class="datum-header">{datum_formatiert}</div>
            <div class="termine-liste">
        '''

        for v in sorted(tage, key=lambda x: (x.uhrzeit == 'ganztägig', x.uhrzeit, x.name)):
            beschreibung_escaped = v.beschreibung.replace('"', '&quot;').replace('\n', ' ')[:200]

            termine_html += f'''
                <div class="termin" data-stadt="{v.stadt}">
                    <div class="termin-zeit">{v.uhrzeit}</div>
                    <div class="termin-info">
                        <div class="termin-name">
                            <a href="{v.link}" target="_blank">{v.name}</a>
                        </div>
                        <div class="termin-stadt">{v.stadt}</div>
                        {f'<div class="termin-ort">{v.ort}</div>' if v.ort else ''}
                        {f'<div class="termin-beschreibung">{beschreibung_escaped}</div>' if beschreibung_escaped else ''}
                    </div>
                </div>
            '''

        termine_html += '''
            </div>
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
        }}

        .termin-name a {{
            color: var(--text-color);
            text-decoration: none;
        }}

        .termin-name a:hover {{
            color: var(--accent-color);
            text-decoration: underline;
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

        <div class="filter-bar">
            <select id="stadt-filter" onchange="filterTermine()">
                {filter_html}
            </select>
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
            const filter = document.getElementById('stadt-filter').value;
            const termine = document.querySelectorAll('.termin');
            let sichtbar = 0;

            termine.forEach(t => {{
                if (!filter || t.dataset.stadt === filter) {{
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

        veranstaltungen = hole_veranstaltungen(j, m)
        staedte = len(set(v.stadt for v in veranstaltungen if v.stadt))
        print(f"  → {len(veranstaltungen)} Veranstaltungen in {staedte} Orten")

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
