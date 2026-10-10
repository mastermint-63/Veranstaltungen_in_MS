"""XSS-Regressionstests (Audit 10.10.2026, Befund #3): Fremde Felder aus den
Quellen duerfen weder aus dem href-Attribut noch aus dem Text ausbrechen."""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import generiere_html
from scraper import Veranstaltung


def _html(**kwargs):
    defaults = dict(
        name='Konzert', datum=datetime(2026, 10, 10, 20), uhrzeit='20:00 Uhr',
        ort='Halle', stadt='Münster', link='', beschreibung='', quelle='muensterland',
        kategorie='',
    )
    defaults.update(kwargs)
    return generiere_html([Veranstaltung(**defaults)], 2026, 10, [(2026, 10)])


def test_link_kann_href_nicht_verlassen():
    html = _html(link='https://example.org/a"onmouseover="alert(1)')
    assert '"onmouseover="' not in html
    assert 'href="https://example.org/a&quot;onmouseover=&quot;alert(1)"' in html


def test_link_mit_spitzer_klammer_bleibt_im_attribut():
    html = _html(link='https://example.org/"><script>alert(1)</script>')
    assert '<script>alert(1)' not in html


def test_script_in_textfeldern_wird_escaped():
    html = _html(name='<script>alert("n")</script>', ort='<script>alert("o")</script>',
                 stadt='<script>alert("s")</script>',
                 beschreibung='<script>alert("b")</script>', kategorie='<b>k</b>')
    assert '<script>alert(' not in html
    assert '&lt;script&gt;' in html
    assert '<b>k</b>' not in html


def test_javascript_link_wird_kein_href():
    for link in ('javascript:alert(1)', 'JaVaScRiPt:alert(1)', ' javascript:alert(1)',
                 'data:text/html,<script>alert(1)</script>'):
        html = _html(name='Boese', link=link)
        assert 'href="javascript' not in html.lower(), link
        assert 'href="data:' not in html, link
        assert 'href=" javascript' not in html.lower(), link
