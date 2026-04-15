"""Tests für Dedup-Logik in app.py."""
import sys
import os
from datetime import datetime

# app.py liegt im Parent-Verzeichnis
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scraper import Veranstaltung
from app import _normalisiere, _veranstaltung_score, entferne_duplikate


def _veranstaltung(name, quelle='muensterland', link='', uhrzeit='',
                   beschreibung='', ort='', stadt='Münster', kategorie=''):
    return Veranstaltung(
        name=name,
        datum=datetime(2026, 4, 15),
        uhrzeit=uhrzeit,
        ort=ort,
        stadt=stadt,
        link=link,
        beschreibung=beschreibung,
        quelle=quelle,
        kategorie=kategorie,
    )


# --- _normalisiere ---

def test_normalisiere_lowercase():
    assert _normalisiere('Großes Konzert') == 'großes konzert'


def test_normalisiere_sonderzeichen():
    assert _normalisiere('Konzert! (Live)') == 'konzert live'


def test_normalisiere_whitespace():
    assert _normalisiere('  Viel   Platz  ') == 'viel platz'


def test_normalisiere_leer():
    assert _normalisiere('') == ''


# --- _veranstaltung_score ---

def test_score_leer():
    t = _veranstaltung('Konzert')
    assert _veranstaltung_score(t) == 0


def test_score_link():
    t = _veranstaltung('Konzert', link='https://example.com')
    assert _veranstaltung_score(t) == 2


def test_score_uhrzeit():
    t = _veranstaltung('Konzert', uhrzeit='20:00 Uhr')
    assert _veranstaltung_score(t) == 2


def test_score_uhrzeit_ganztaegig_kein_bonus():
    t = _veranstaltung('Konzert', uhrzeit='ganztägig')
    assert _veranstaltung_score(t) == 0


def test_score_uhrzeit_laufend_kein_bonus():
    t = _veranstaltung('Konzert', uhrzeit='laufend')
    assert _veranstaltung_score(t) == 0


def test_score_uhrzeit_siehe_website_kein_bonus():
    t = _veranstaltung('Konzert', uhrzeit='siehe Website')
    assert _veranstaltung_score(t) == 0


def test_score_beschreibung():
    t = _veranstaltung('Konzert', beschreibung='Tolles Event')
    assert _veranstaltung_score(t) == 1


def test_score_ort():
    t = _veranstaltung('Konzert', ort='Halle Münsterland')
    assert _veranstaltung_score(t) == 1


def test_score_alles():
    t = _veranstaltung('Konzert', link='https://x.de', uhrzeit='20:00 Uhr',
                       beschreibung='Text', ort='Ort')
    assert _veranstaltung_score(t) == 6


# --- entferne_duplikate ---

def test_exakte_duplikate():
    a = _veranstaltung('Konzert', link='https://a.de', uhrzeit='20:00 Uhr')
    b = _veranstaltung('Konzert', link='https://b.de')
    ergebnis = entferne_duplikate([a, b])
    assert len(ergebnis) == 1
    assert ergebnis[0].link == 'https://a.de'  # höherer Score


def test_teilstring_duplikat():
    lang = _veranstaltung('Großes Sommerkonzert im Park', link='https://a.de', uhrzeit='20:00 Uhr')
    kurz = _veranstaltung('Sommerkonzert im Park', link='https://b.de')
    ergebnis = entferne_duplikate([lang, kurz])
    assert len(ergebnis) == 1


def test_verschiedene_bleiben():
    a = _veranstaltung('Konzert', link='https://a.de')
    b = _veranstaltung('Theater', link='https://b.de')
    ergebnis = entferne_duplikate([a, b])
    assert len(ergebnis) == 2


def test_verschiedene_tage_kein_duplikat():
    a = _veranstaltung('Konzert', link='https://a.de')
    b = Veranstaltung(
        name='Konzert', datum=datetime(2026, 4, 16),
        uhrzeit='', ort='', stadt='Münster', link='https://b.de',
        quelle='muensterland',
    )
    ergebnis = entferne_duplikate([a, b])
    assert len(ergebnis) == 2


def test_hoeherer_score_gewinnt():
    reich = _veranstaltung('Konzert', link='https://a.de', uhrzeit='20:00 Uhr',
                           beschreibung='Text', ort='Halle')
    arm = _veranstaltung('Konzert')
    ergebnis = entferne_duplikate([arm, reich])
    assert len(ergebnis) == 1
    assert ergebnis[0].link == 'https://a.de'


def test_leere_liste():
    assert entferne_duplikate([]) == []


def test_einzelnes_element():
    a = _veranstaltung('Konzert')
    ergebnis = entferne_duplikate([a])
    assert len(ergebnis) == 1
