"""Form: Kantenklassifikation und die vier Stilregeln an gebauten Gegenfällen.

Jede Regel wird an einem Körper geprüft, bei dem man das Ergebnis vorher hinschreiben
kann -- zwei versetzte Quader, ein Schlitz, ein Loch, eine Rundung. Erst danach an den
Referenzteilen (`spec/test_tray_r1.py`, `spec/test_hopper_floor.py`), wo niemand die
Zahl vorher kennt.
"""
import numpy as np
import pytest
from build123d import Axis, Box, Cylinder, Location, Pos, fillet

from pruefstand import (Body, absatz, kanten, kerbe, load_form, splitter, unverrundet)
from pruefstand.form import KONKAV, KONVEX, TANGENTIAL, SCHEMA, load_form as _lf
from pruefstand.teile import SCHEMA as TEILE_SCHEMA
from pruefstand.results import forget_open


def teil(solid, key='P') -> Body:
    return Body(key, key, solid=solid)


def stufe(versatz=1.5, key='P') -> Body:
    """Zwei 20er-Quader übereinander, der obere um `versatz` in X verschoben.

    Genau Marcs Bild in klein: die Kontur läuft nicht durch, sondern springt. Auf der
    einen Seite entsteht ein Absatz nach innen, auf der anderen einer nach außen.
    """
    return teil((Box(20, 20, 10) + Pos(versatz, 0, 10) * Box(20, 20, 10)).solid(), key)


def schlitz(breite=1.0, key='P') -> Body:
    """Klotz mit einem Schlitz von `breite` -- die Gegenwand steht sich selbst gegenüber."""
    return teil((Box(30, 20, 10) - Pos(0, 0, 2) * Box(breite, 30, 10)).solid(), key)


# -- kanten(): die Grundlage ------------------------------------------------

def test_quader_hat_zwoelf_konvexe_kanten():
    ks = kanten(teil(Box(10, 10, 10).solid()))
    assert len(ks) == 12
    assert all(k.art == KONVEX for k in ks), [k.art for k in ks]
    assert all(k.knick_deg == pytest.approx(90.0) for k in ks)
    assert all(k.typ == 'Line' for k in ks)
    assert sum(k.laenge_mm for k in ks) == pytest.approx(120.0)


def test_innenecke_ist_konkav():
    """Aus einem Quader eine Ecke geschnitten: genau eine der 18 Kanten ist innen."""
    l_profil = Box(20, 20, 10) - Pos(5, 5, 0) * Box(12, 12, 12)
    ks = kanten(teil(l_profil.solid()))
    konkav = [k for k in ks if k.art == KONKAV]
    assert len(ks) == 18
    assert len(konkav) == 1, [str(k) for k in ks]
    assert konkav[0].knick_deg == pytest.approx(90.0)


def test_rundung_ist_tangential_und_nicht_konvex():
    """Eine verrundete Kante hat zwei Übergänge mit Knick 0 -- da ist keine Ecke."""
    w = Box(20, 20, 10)
    ks = kanten(teil(fillet(w.edges(), radius=2.0).solid()))
    assert all(k.art != KONKAV for k in ks)
    assert sum(1 for k in ks if k.art == TANGENTIAL) > 0
    assert all(k.knick_deg < 1.0 for k in ks if k.art == TANGENTIAL)


def test_kante_kennt_ihre_flaechen_und_ihre_halbierende():
    ks = kanten(teil(Box(10, 10, 10).solid(), key='K'))
    k = max(ks, key=lambda x: x.mitte[2])
    assert len(k.flaechen) == 2 and all(f.startswith('K#') for f in k.flaechen)
    assert np.linalg.norm(k.halbierende) == pytest.approx(1.0)
    assert k.halbierende[2] > 0, 'die Halbierende einer oberen Kante zeigt nach oben'


def test_netzkoerper_hat_keine_kanten(tmp_path):
    """Ein Dreiecksnetz knickt an jeder Facette -- daran ist nichts zu messen."""
    from build123d import export_stl
    from pruefstand import load_mesh
    p = tmp_path / 'w.stl'
    export_stl(Box(10, 10, 10).solid(), str(p))
    b = load_mesh(p, key='M')
    assert kanten(b) == []
    for regel in (absatz, kerbe, unverrundet, splitter):
        r = regel(b)
        assert r.unentschieden and 'kein BRep' in r.offen_grund
        assert not r.passed
    assert len(forget_open()) == 4


# -- Regel: absatz ----------------------------------------------------------

def test_versetzte_quader_geben_einen_absatz_je_seite():
    r = absatz(stufe(1.5))
    assert r.anzahl == 2, r.absaetze
    assert all(a['versatz_mm'] == pytest.approx(1.5) for a in r.absaetze)
    assert all(a['laenge_mm'] == pytest.approx(20.0) for a in r.absaetze)
    assert r.max_versatz_mm == pytest.approx(1.5)
    assert not r.passed
    assert r.urteil_auf == 'brep'


def test_buendige_quader_geben_keinen_absatz():
    assert absatz(stufe(0.0)).anzahl == 0
    assert absatz(stufe(0.0)).passed


def test_grosser_versatz_ist_eine_stufe_und_kein_absatz():
    """5 mm ist eine Form, kein Konturfehler -- die Regel endet bei 3 mm."""
    assert absatz(stufe(5.0)).anzahl == 0


def test_winziger_versatz_ist_eine_naht_und_kein_absatz():
    assert absatz(stufe(0.1)).anzahl == 0


def test_absatz_meldet_ort_flaechen_und_kanten():
    a = absatz(stufe(1.2)).absaetze[0]
    assert set(a) == {'ort', 'versatz_mm', 'laenge_mm', 'sorte', 'flaechen', 'stufe_mm2',
                      'kanten'}
    assert len(a['flaechen']) == 3 and len(a['kanten']) == 2
    assert a['ort'][2] == pytest.approx(5.0, abs=5.0)


def platte(zusatz, key='P') -> Body:
    """Platte 60 x 40 x 4 (dünn in Z) plus ein angesetzter Block -- die drei Sorten."""
    return teil((Box(60, 40, 4) + zusatz).solid(), key)


def test_absatz_sorten_umriss_banddicke_pad():
    """Die drei Sorten, je an einem Körper, bei dem man die Antwort vorher kennt.

    Verfahren wie in `rocking-photo-tray-r7/src/t41_details.py`: die Sorte folgt aus
    den Normalen der beiden Wände und der Stufe, bezogen auf die Plattenachse (hier
    Z, die dünnste Richtung).
    """
    # Pad: ein 1,5 mm hoher Block auf der großen Fläche -- beide Wände sind
    # Plattenflächen (Normale längs Z).
    pad = absatz(platte(Pos(0, 0, 2.75) * Box(10, 10, 1.5)))
    assert pad.anzahl == 4, 'eine Kante je Blockseite'
    assert pad.sorten == {'umriss': 0, 'banddicke': 0, 'pad': 4}
    assert pad.achse == [0.0, 0.0, 1.0]

    # Banddicke: die untere Hälfte der Stirnseite steht 1 mm vor -- die Stufe liegt
    # in einer Z-Ebene, die Wände stehen quer.
    band = absatz(platte(Pos(30.5, 0, -1) * Box(1, 40, 2)))
    assert band.sorten['banddicke'] == 1 and band.sorten['umriss'] == 0
    stufe = [a for a in band.absaetze if a['sorte'] == 'banddicke'][0]
    assert stufe['versatz_mm'] == pytest.approx(1.0) and stufe['laenge_mm'] == pytest.approx(40.0)
    # Der zweite Befund desselben Körpers ist die Unterseite des Blocks gegen die
    # Plattenunterseite -- zwei Plattenflächen als Wände, also `pad`. Richtig sortiert.
    assert band.sorten['pad'] == 1

    # Umriss: ein Stück der Stirnseite steht über die volle Dicke vor -- die Stufe
    # liegt quer zur Platte, die Silhouette springt.
    umriss = absatz(platte(Pos(30.5, 10, 0) * Box(1, 20, 4)))
    assert umriss.sorten == {'umriss': 1, 'banddicke': 0, 'pad': 0}
    assert umriss.absaetze[0]['versatz_mm'] == pytest.approx(1.0)


def test_absatz_achse_ist_ueberschreibbar():
    """Die Plattenachse ist eine Annahme -- also muss man sie setzen können."""
    r = absatz(platte(Pos(0, 0, 2.75) * Box(10, 10, 1.5)), achse=(1, 0, 0))
    assert r.achse == [1.0, 0.0, 0.0]
    assert all(a['sorte'] != 'pad' for a in r.absaetze), 'andere Achse, andere Lesart'
    assert any(a.get('plattenachse_gesetzt') for a in r.annahmen)


# -- Regel: kerbe -----------------------------------------------------------

def test_schlitz_ohne_partner_wird_gemeldet():
    r = kerbe(schlitz(1.0))
    assert r.anzahl >= 1
    assert r.unerklaert == r.anzahl
    assert min(z['spalt_mm'] for z in r.zonen) == pytest.approx(1.0, abs=0.01)
    assert not r.passed
    assert r.urteil_auf == 'brep'
    assert forget_open() == []


def test_breiter_schlitz_ist_keine_kerbe():
    """4 mm sind ein Durchgang. Die Regel endet bei 2,5 mm."""
    assert kerbe(schlitz(4.0)).anzahl == 0


def test_schlitz_mit_partner_ist_erklaert():
    """Steckt etwas im Schlitz, ist er eine Passung und kein Fehler."""
    feder = teil(Box(0.9, 30, 8).locate(Location((0, 0, 1))).solid(), key='F')
    r = kerbe(schlitz(1.0), [feder])
    assert r.anzahl >= 1
    assert r.unerklaert == 0, [z for z in r.zonen if not z['erklaert']]
    assert all(z['partner'] == 'F' for z in r.zonen)
    assert r.passed


def test_schlitz_mit_erklaerung_aus_der_pflegedatei(tmp_path):
    p = tmp_path / 'form.yaml'
    p.write_text(f"""schema: {SCHEMA}
teile:
  - key: P
    erklaert:
      - name: Kabelschlitz
        bereich: {{frame: world, von: [-5, -20, -10], bis: [5, 20, 10]}}
        grund: Kabelführung, bleibt offen
""")
    spec = load_form(p)
    r = kerbe(schlitz(1.0), erklaert=spec.teil('P'))
    assert r.unerklaert == 0
    assert all('Kabelschlitz' in z['grund'] for z in r.zonen)


def test_kerbe_meldet_den_naechsten_fremdkoerper_auch_wenn_er_zu_weit_weg_ist():
    weit = teil(Box(5, 5, 5).locate(Location((40, 0, 0))).solid(), key='W')
    r = kerbe(schlitz(1.0), [weit])
    z = r.zonen[0]
    assert not z['erklaert']
    assert z['partner'] == 'W'
    assert z['partner_mm'] > 2.5


def partner_unter(abstand=3.7, key='N') -> Body:
    """Ein Nachbarkörper, dessen Oberseite `abstand` unter dem Schlitzgrund liegt.

    Genau die Lage der R6d-Rahmenfugen: der Sitz ist breit, das Teil, das er aufnimmt,
    beginnt erst einige Millimeter weiter (Fuge plus Materialstärke dazwischen).
    """
    oben = -3.0 - float(abstand)          # Schlitzgrund von `schlitz()` liegt bei z = −3
    return teil(Box(30, 20, 4).locate(Location((0, 0, oben - 2.0))).solid(), key)


def test_breiter_sitz_erklaert_einen_partner_in_vier_millimetern():
    """Der Ankerradius wächst mit der Spaltbreite: 3 x 1,45 mm = 4,35 mm.

    Der Befund aus `r7-analyse-bericht.md` (Werkzeuglücke 2): 13 Sitze an T40/T41 mit
    Partner in 3,7--4,0 mm standen als unerklärte Kerben im Bericht, obwohl sie die
    Rahmenverschraubung sind. Ein fester Radius von 2,5 mm verfehlt sie, ein Faktor 2
    (2,90 mm) ebenfalls.
    """
    r = kerbe(schlitz(1.45), [partner_unter(3.7)])
    assert r.anzahl >= 1
    assert min(z['spalt_mm'] for z in r.zonen) == pytest.approx(1.45, abs=0.01)
    assert all(z['partner_mm'] == pytest.approx(3.7, abs=0.05) for z in r.zonen)
    assert all(z['anker_mm'] == pytest.approx(4.35, abs=0.01) for z in r.zonen)
    assert r.unerklaert == 0, [z for z in r.zonen if not z['erklaert']]


def test_schmaler_schlitz_bekommt_denselben_partner_nicht_geschenkt():
    """0,34 mm Spalt: 3 x 0,34 liegt unter 2,5 mm, also bleibt es bei 2,5 mm.

    Das ist die Gegenprobe zum Test darüber -- die Regel darf nicht jede Stelle
    erklären, nur weil irgendwo ein Körper in vier Millimetern liegt. Die 0,34-mm-Nut
    an T41 (lokal Z 264) muss gemeldet bleiben; sie ist schmaler als eine Bahn.
    """
    r = kerbe(schlitz(0.34), [partner_unter(3.7)])
    assert r.anzahl >= 1
    assert all(z['anker_mm'] == pytest.approx(2.5) for z in r.zonen)
    assert r.unerklaert == r.anzahl


def test_anker_aus_der_pflegedatei_schlaegt_die_hausregel(tmp_path):
    p = tmp_path / 'form.yaml'
    p.write_text(f"""schema: {SCHEMA}
teile:
  - key: P
    anker_mm: 4.0
""")
    spec = load_form(p).teil('P')
    assert spec.anker_mm == 4.0
    r = kerbe(schlitz(0.34), [partner_unter(3.7)], erklaert=spec)
    assert all(z['anker_mm'] == pytest.approx(4.0) for z in r.zonen)
    assert r.unerklaert == 0
    # Das Aufrufargument bleibt das letzte Wort -- sonst überschriebe die Pflegedatei
    # still einen Wert, den ein Test bewusst gesetzt hat.
    eng = kerbe(schlitz(0.34), [partner_unter(3.7)], erklaert=spec, anker_mm=2.5)
    assert eng.unerklaert == eng.anzahl


def test_kerbe_ohne_kontext_sagt_es_im_budget():
    r = kerbe(schlitz(1.0))
    assert any(u.get('was') == 'kontext' for u in r.uebersprungen)


# -- Regel: unverrundet -----------------------------------------------------

def test_scharfer_quader_meldet_alle_zwoelf_kanten():
    r = unverrundet(teil(Box(20, 20, 20).solid()))
    assert r.anzahl == 12
    assert r.gesamt_mm == pytest.approx(240.0)
    assert r.radius_mm == pytest.approx(4.2)
    assert not r.passed


def test_verrundeter_quader_meldet_nichts():
    w = Box(20, 20, 20)
    assert unverrundet(teil(fillet(w.edges(), radius=4.2).solid())).anzahl == 0


def test_kurze_kanten_zaehlen_nicht():
    """Unter 5 mm ist eine Kante zu kurz, als dass R4,2 dort etwas änderte."""
    assert unverrundet(teil(Box(4, 4, 4).solid())).anzahl == 0


def test_bohrungsmuendung_ist_keine_aussenkante():
    """Ein Ø8-Loch hat einen scharfen Rand -- aber R4,2 passt da nicht hinein."""
    klotz = Box(20, 20, 10) - Cylinder(4, 30)
    r = unverrundet(teil(klotz.solid()))
    assert r.anzahl == 12, [k['typ'] for k in r.kanten]
    assert all(k['typ'] == 'Line' for k in r.kanten)


def test_kante_am_taschenboden_ist_keine_aussenkante():
    """Am Boden einer Tasche greift niemand an -- der Strahl nach außen trifft die Wand.

    Gemeldet werden die zwölf Kanten der Außenhülle und die vier des Taschenrands; die
    vier konvexen Kanten am Taschenboden (z = -5) stehen nicht darunter.
    """
    topf = Box(30, 30, 20) - Pos(0, 0, 5) * Box(20, 20, 20)
    r = unverrundet(teil(topf.solid()))
    assert r.anzahl == 16, r.kanten
    assert not any(k['ort'][2] == pytest.approx(-5.0) for k in r.kanten), r.kanten


def test_druckpose_nimmt_die_bettseite_heraus():
    """Liegt der Quader auf dem Bett, sind seine vier unteren Kanten kein Befund."""
    w = teil(Box(20, 20, 20).locate(Location((0, 0, 10))).solid())
    assert unverrundet(w).anzahl == 12
    r = unverrundet(w, pose={'rotate': [0, 0, 0]})
    assert r.anzahl == 8, [k['ort'] for k in r.kanten]
    assert all(k['ort'][2] > 0.5 for k in r.kanten)


def test_ohne_teile_yaml_ist_die_zahl_eine_obergrenze():
    """Ohne Druckpose und ohne Kontext zählen Bett- und Fugenkanten mit -- das sagt sie."""
    w = teil(Box(20, 20, 20).locate(Location((0, 0, 10))).solid())
    r = unverrundet(w)
    assert r.anzahl == 12 and r.obergrenze
    assert r.ausnahmen == {'bettseite': False, 'fugenkanten': False, 'griffkanten': None}
    assert r.as_dict()['obergrenze'] is True
    assert any(u.get('was') == 'ausnahme' for u in r.uebersprungen)


def test_mit_auflage_und_kontext_ist_die_zahl_ein_messwert(tmp_path):
    """`teile.yaml` plus Nachbarkörper: Bettkanten und Fugenkanten fallen heraus.

    Der Quader liegt auf dem Bett (vier Kanten unten) und stößt an der Seite an einen
    Nachbarn in 0,1 mm (vier Kanten dort, eine davon zugleich am Bett). Von zwölf
    Kanten bleiben fünf -- und erst dann ist die Zahl keine Obergrenze mehr.
    """
    from pruefstand import load_teile
    w = teil(Box(20, 20, 20).locate(Location((0, 0, 10))).solid())
    nachbar = teil(Box(10, 20, 20).locate(Location((15.1, 0, 10))).solid(), key='N')
    p = tmp_path / 'teile.yaml'
    p.write_text(f"""schema: {TEILE_SCHEMA}
teile:
  - key: P
    auflage: {{normale: [0, 0, -1]}}
    griffkanten: nein
""")
    t = load_teile(p)['P']
    assert t.griffkanten is False and t.schwelle_mm(4.2) == 1.0
    r = unverrundet(w, teil=t, kontext=[nachbar])
    assert not r.obergrenze
    assert r.ausnahmen == {'bettseite': True, 'fugenkanten': True, 'griffkanten': False}
    assert r.radius_mm == 1.0, 'ein Rahmenteil bekommt den Kantenbruch, nicht R4,2'
    assert r.anzahl == 5, [k['ort'] for k in r.kanten]
    assert all(k['ort'][2] > 0.5 for k in r.kanten), 'keine Bettkante mehr'
    assert all(k['ort'][0] < 9.0 for k in r.kanten), 'keine Kante an der Fuge mehr'


def test_auflage_als_region_nimmt_dieselben_kanten_heraus(tmp_path):
    from pruefstand import load_teile
    w = teil(Box(20, 20, 20).locate(Location((0, 0, 10))).solid())
    p = tmp_path / 'teile-region.yaml'
    p.write_text(f"""schema: {TEILE_SCHEMA}
teile:
  - key: P
    auflage: {{region: {{von: [-11, -11, -1], bis: [11, 11, 0.5]}}}}
""")
    r = unverrundet(w, teil=load_teile(p)['P'])
    assert r.anzahl == 8
    assert r.radius_mm == 4.2, 'ohne griffkanten-Angabe bleibt es bei der Hausregel'


def test_teile_yaml_wird_streng_geprueft(tmp_path):
    from pruefstand import TeileSpecFehler, load_teile
    p = tmp_path / 'kaputt.yaml'
    for text, stueck in [
        ('schema: falsch/1\nteile: []', 'schema'),
        (f'schema: {TEILE_SCHEMA}\nteile: []', 'teile'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{pose: null}}]', 'key'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P, quatsch: 1}}]', 'unbekannte Schlüssel'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P, griffkanten: vielleicht}}]', 'griffkanten'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P, auflage: {{}}}}]', 'genau eines'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P, auflage: {{normale: [0,0,0]}}}}]', 'Nullvektor'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P, radius_mm: -1}}]', 'radius_mm'),
        (f'schema: {TEILE_SCHEMA}\nteile: [{{key: P}}, {{key: P}}]', 'doppelt'),
    ]:
        p.write_text(text)
        with pytest.raises(TeileSpecFehler, match=stueck):
            load_teile(p)


# -- Regel: splitter --------------------------------------------------------

def test_sauberer_quader_hat_keine_splitter():
    r = splitter(teil(Box(20, 20, 10).solid()))
    assert r.anzahl == 0 and r.passed


def test_schmale_stufe_hinterlaesst_kanten_unter_der_bahnbreite():
    """0,3 mm Versatz: die Stirnkanten der Stufe sind schmaler als eine Druckbahn."""
    r = splitter(stufe(0.3))
    assert len(r.kurze_kanten) == 4, r.kurze_kanten
    assert all(k['laenge_mm'] == pytest.approx(0.3) for k in r.kurze_kanten)
    assert not r.passed


def test_winzige_flaeche_zwischen_grossen_nachbarn():
    """0,04 mm Versatz: die Stufe ist 0,8 mm² groß und klebt an zwei 200-mm²-Wänden."""
    r = splitter(stufe(0.04))
    assert len(r.winzige_flaechen) == 2, r.as_dict()
    assert all(f['mm2'] == pytest.approx(0.8, abs=0.01) for f in r.winzige_flaechen)
    assert all(f['groesster_nachbar_mm2'] > 100 for f in r.winzige_flaechen)


def test_zylindernaht_ist_kein_splitter():
    """Ein Zylinder schließt sich an einer Naht -- beide Nachbarn sind dieselbe Fläche.

    Ohne diese Unterscheidung meldete die Wanne 14 „unverschmolzene" Kanten, alle an
    Rundzapfen und Bohrungen, und keine davon wäre ein Befund gewesen.
    """
    r = splitter(teil(Cylinder(5, 20).solid()))
    assert r.unverschmolzen == []
    assert r.anzahl == 0


def test_filletuebergang_ist_kein_splitter():
    """Ein sauber tangentialer Fillet ist ein Merkmal, kein Rest.

    Vier verrundete Senkrechte am Quader ergeben acht Übergänge mit Knick 0° zwischen
    Ebene und Zylinder. Die alte Regel meldete sie als „unverschmolzen" -- an der
    Wanne R2 16 Stück, an T41 20 bzw. 16, an T01 und C07 **alle** Treffer
    (`var/etappe4-bericht.md`, `r7-analyse-bericht.md` Werkzeuglücke 4). Gezählt
    werden sie weiter, nur eben als das, was sie sind.
    """
    w = Box(20, 20, 10)
    verrundet = teil(fillet(w.edges().filter_by(Axis.Z), radius=2.0).solid())
    r = splitter(verrundet)
    assert r.unverschmolzen == [], r.unverschmolzen
    assert len(r.rundungsuebergaenge) == 8, r.rundungsuebergaenge
    assert all('CYLINDER' in u['flaechentypen'] for u in r.rundungsuebergaenge)
    assert r.anzahl == 0 and r.passed


def test_zwei_ebenen_ohne_knick_bleiben_ein_splitter():
    """Die Gegenprobe: Ebene auf Ebene mit Knick 0 ist wirklich eine Boolesche Spur.

    Gebaut wird sie mit dem rohen Boolean des Kerns, **ohne** das abschließende
    Aufräumen -- build123ds `+` legt gleichliegende Ebenen von selbst zusammen, ein
    STEP aus fremder Hand tut das nicht. Genau daher kommen die Fälle, die die Regel
    finden soll: zehn Flächen statt acht, vier Kanten mitten in zwei ebenen Wänden.
    """
    from OCP.BRepAlgoAPI import BRepAlgoAPI_Fuse
    from OCP.TopAbs import TopAbs_SOLID
    from OCP.TopExp import TopExp_Explorer
    import build123d as bd
    op = BRepAlgoAPI_Fuse(Box(20, 20, 10).solid().wrapped,
                          (Pos(20, 0, 0) * Box(20, 20, 10)).solid().wrapped)
    op.Build()
    ex = TopExp_Explorer(op.Shape(), TopAbs_SOLID)
    w = teil(bd.Solid(ex.Current()))
    assert len(w.solid.faces()) == 10, 'zwei Flächenpaare zu viel -- so soll es sein'
    r = splitter(w)
    assert r.rundungsuebergaenge == []
    assert len(r.unverschmolzen) == 4, r.unverschmolzen
    assert all(u['flaechentypen'] == ['PLANE', 'PLANE'] for u in r.unverschmolzen)
    assert all(u['knick_deg'] == pytest.approx(0.0, abs=1e-6) for u in r.unverschmolzen)
    assert r.anzahl == 4 and not r.passed


# -- Pflegedatei form.yaml --------------------------------------------------

def test_form_yaml_wird_streng_geprueft(tmp_path):
    p = tmp_path / 'form.yaml'
    for text, stueck in [
        ('schema: falsch/1\nteile: []', 'Schema'),
        (f'schema: {SCHEMA}\nteile: []', 'teile'),
        (f'schema: {SCHEMA}\nteile: [{{erklaert: []}}]', 'key'),
        (f'schema: {SCHEMA}\nteile: [{{key: P, quatsch: 1}}]', 'unbekannte Schlüssel'),
        (f'schema: {SCHEMA}\nteile: [{{key: P, erklaert: [{{name: a}}]}}]', 'bereich'),
        (f'schema: {SCHEMA}\nteile:\n  - key: P\n    erklaert:\n'
         '      - {name: a, bereich: {von: [0,0,0], bis: [1,1,1]}}\n'
         '      - {name: a, bereich: {von: [0,0,0], bis: [1,1,1]}}\n', 'doppelte Namen'),
    ]:
        p.write_text(text)
        with pytest.raises(ValueError, match=stueck):
            _lf(p)


def test_form_yaml_fehlt(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_form(tmp_path / 'gibt-es-nicht.yaml')


def test_erklaerte_zone_trifft_nur_innerhalb(tmp_path):
    p = tmp_path / 'form.yaml'
    p.write_text(f"""schema: {SCHEMA}
teile:
  - key: P
    erklaert:
      - name: Nut
        bereich: {{von: [0, 0, 0], bis: [10, 10, 10]}}
        grund: Kabel
""")
    t = load_form(p).teil('P')
    assert t.trifft((5, 5, 5)) == 'Nut'
    assert t.trifft((5, 5, 15)) == ''
    assert load_form(p).teil('gibt-es-nicht') is None
