"""Die HTML-Seite zusammensetzen: eine Datei, offline lauffähig."""
from __future__ import annotations

import base64
import html
import json
from pathlib import Path

from . import geometry
from .model import OUTCOME_LABEL, OUTCOME_ORDER, Bericht, projekt_wurzel

ASSETS = Path(__file__).parent / 'assets'


def _asset(name: str) -> str:
    return (ASSETS / name).read_text()


def _png_data_uri(pfad) -> str | None:
    try:
        p = Path(pfad)
        if not p.exists() or p.stat().st_size > 4_000_000:
            return None
        return 'data:image/png;base64,' + base64.b64encode(p.read_bytes()).decode('ascii')
    except Exception:
        return None


def daten(bericht: Bericht, szene: geometry.Szene) -> dict:
    tests = []
    for t in bericht.tests:
        ms = []
        for w in t.messwerte:
            marker = None
            if w.marker and w.marker.get('art') == 'strecke':
                marker = dict(w.marker)
            elif w.marker and w.marker.get('art') == 'ueberschneidung':
                kaesten = []
                for ka, kb in w.marker.get('paare', []):
                    box = geometry.huell_schnitt(szene.by_key(ka), szene.by_key(kb))
                    if box:
                        box['paar'] = [ka, kb]
                        kaesten.append(box)
                if kaesten:
                    marker = {'art': 'kaesten', 'kaesten': kaesten, 'label': w.marker.get('label', '')}
            ms.append({
                'mid': w.mid, 'primitive': w.primitive, 'titel': w.titel,
                'zeilen': [list(z) for z in w.zeilen], 'koerper': w.koerper,
                'marker': marker, 'hinweis': w.hinweis, 'schwere': w.schwere,
                'png': _png_data_uri(w.png) if w.png else None,
            })
        tests.append({
            'tid': t.tid, 'nodeid': t.nodeid, 'name': t.name, 'datei': t.datei,
            'outcome': t.outcome, 'label': OUTCOME_LABEL.get(t.outcome, t.outcome),
            'dauer_s': t.dauer_s, 'messwerte': ms,
            'koerper': t.koerper,
        })
    z = bericht.zaehlung()
    ampel = [{'outcome': o, 'label': OUTCOME_LABEL.get(o, o), 'anzahl': z[o]}
             for o in OUTCOME_ORDER if o in z]
    ampel += [{'outcome': o, 'label': OUTCOME_LABEL.get(o, o), 'anzahl': n}
              for o, n in z.items() if o not in OUTCOME_ORDER]
    return {
        'kopf': {
            'projekt': bericht.projekt,
            'maschine': szene.maschine_name,
            'revision': szene.maschine_revision,
            'erzeugt': bericht.erzeugt,
            'bericht': str(bericht.pfad),
            'tests_gesamt': len(bericht.tests),
        },
        'ampel': ampel,
        'tests': tests,
        'koerper': [geometry.payload(k) for k in szene.koerper if k.mesh is not None],
        'warnungen': szene.warnungen,
    }


def seite(d: dict) -> str:
    kopf = d['kopf']
    titel = f"Prüfstand – {kopf['projekt'] or 'Bericht'}"
    js_daten = json.dumps(d, ensure_ascii=False, separators=(',', ':'))
    js_daten = js_daten.replace('</', '<\\/')
    return f"""<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="utf-8">
<title>{html.escape(titel)}</title>
<style>
{_asset('style.css')}
</style>
</head>
<body>
<header id="kopf">
  <div class="titel">
    <h1>{html.escape(kopf['projekt'] or 'Prüfbericht')}</h1>
    <div class="meta"></div>
  </div>
  <div class="ampel" id="ampel"></div>
</header>
<main>
  <aside id="liste"></aside>
  <section id="buehne">
    <div id="canvas"></div>
    <div id="hud">
      <div id="hud-titel">Prüfbericht</div>
      <div id="hud-text">Einen Befund links anklicken.</div>
    </div>
    <div id="legende"></div>
  </section>
</main>
<script type="application/json" id="daten">{js_daten}</script>
<script>
{_asset('three.min.js')}
</script>
<script>
{_asset('OrbitControls.js')}
</script>
<script>
{_asset('viewer.js')}
</script>
</body>
</html>
"""


def build(bericht_json, out_html) -> Path:
    from . import model
    bericht = model.lade(bericht_json)
    projekt = projekt_wurzel(Path(bericht_json))
    szene = geometry.baue_szene(Path(bericht_json).resolve(), projekt, bericht.alle_koerper())
    d = daten(bericht, szene)
    out = Path(out_html)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(seite(d), encoding='utf-8')
    return out
