"""Tests: Veranstaltungen mit None in Textfeldern dürfen die Pipeline nicht crashen.

Hintergrund: Seit Anfang Juli 2026 crashte app.py täglich in generiere_html()
an html.escape(v.stadt) mit stadt=None (AttributeError). Dadurch wurde
index.html nie neu geschrieben und zeigte auf eine gelöschte Monatsdatei (404).
"""
import os
import sys
from datetime import datetime

# app.py liegt im Parent-Verzeichnis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import generiere_html
from scraper import Veranstaltung


def _veranstaltung(**kwargs):
    defaults = dict(
        name='Testkonzert',
        datum=datetime(2026, 9, 15),
        uhrzeit='19:00',
        ort='Halle',
        stadt='Münster',
        link='https://example.org',
        beschreibung='Beschreibung',
        quelle='muensterland',
        kategorie='',
    )
    defaults.update(kwargs)
    return Veranstaltung(**defaults)


def test_none_textfelder_werden_zu_leerstring():
    v = _veranstaltung(stadt=None, uhrzeit=None, ort=None,
                       link=None, beschreibung=None, kategorie=None)
    assert v.stadt == ''
    assert v.uhrzeit == ''
    assert v.ort == ''
    assert v.link == ''
    assert v.beschreibung == ''
    assert v.kategorie == ''


def test_generiere_html_mit_stadt_none_crasht_nicht():
    veranstaltungen = [
        _veranstaltung(name='Mit Stadt'),
        _veranstaltung(name='Ohne Stadt', stadt=None),
    ]
    html = generiere_html(veranstaltungen, 2026, 9, [(2026, 9)])
    assert 'Mit Stadt' in html
    assert 'Ohne Stadt' in html


def test_sortierung_mit_none_uhrzeit_crasht_nicht():
    a = _veranstaltung(name='A', uhrzeit=None)
    b = _veranstaltung(name='B', uhrzeit='19:00')
    assert sorted([b, a])[0].name == 'A'
