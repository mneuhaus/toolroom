"""pytest-Plugin: Fixtures project/machine, Marker `warnung`, Bericht var/review/pruefstand.json."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from . import context, results
from .context import Project
from .machine import Machine

CONFIG_NAME = 'pruefstand.yaml'
_report: dict = {}


def _find_config(config) -> Path | None:
    cands = []
    for a in list(getattr(config, 'args', []) or []):
        cands.append(Path(str(a).split('::')[0]))
    cands.append(Path(str(config.rootpath)))
    cands.append(Path.cwd())
    seen = set()
    for c in cands:
        p = c.resolve()
        if p.is_file():
            p = p.parent
        while True:
            if p in seen:
                break
            seen.add(p)
            f = p / CONFIG_NAME
            if f.exists():
                return f
            if p.parent == p:
                break
            p = p.parent
    return None


def pytest_configure(config):
    config.addinivalue_line('markers', 'warnung: Fehlschlag wird nur als Warnung gezählt')
    cfg = _find_config(config)
    config._pruefstand_cfg = cfg
    if cfg is None:
        return
    import yaml
    data = yaml.safe_load(cfg.read_text()) or {}
    project = Project.from_spec_dir(cfg.parent, data.get('review'))
    context.set_project(project)
    config._pruefstand_project = project
    config._pruefstand_machine_path = (cfg.parent / data['machine']).resolve() if data.get('machine') else None


@pytest.fixture(scope='session')
def project(pytestconfig):
    p = getattr(pytestconfig, '_pruefstand_project', None)
    if p is None:
        pytest.skip(f'{CONFIG_NAME} nicht gefunden')
    return p


@pytest.fixture(scope='session')
def machine(pytestconfig):
    path = getattr(pytestconfig, '_pruefstand_machine_path', None)
    if path is None:
        pytest.skip(f'kein machine-Eintrag in {CONFIG_NAME}')
    return Machine.load(path)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    context.set_test_id(item.nodeid)
    yield
    context.set_test_id(None)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    out = yield
    rep = out.get_result()
    # Ein Test, in dem ein Primitiv nichts zu messen hatte oder in dem das Messverfahren
    # gescheitert ist, darf nicht grün durchgehen.
    if rep.when == 'call' and rep.passed and not hasattr(rep, 'wasxfail'):
        technik = results.technical_reasons(item.nodeid)
        if technik:
            rep.outcome = 'failed'
            rep.longrepr = '\n'.join([results.TECHNIK_MELDUNG, *technik])
        elif results.open_reasons(item.nodeid):
            # Kein Urteil, aber auch kein erkannter Geometriefehler: eigener Ausgang.
            rep.outcome = 'unentschieden'
            rep.longrepr = '\n'.join([results.OFFEN_MELDUNG, *results.open_reasons(item.nodeid)])
            # An der Sitzung merken, nicht am Modul: ein innerer pytester-Lauf teilt
            # sich den Prozess mit dem äußeren und sähe sonst dessen Ergebnisse.
            item.config._pruefstand_unentschieden = True
        else:
            gruende = results.empty_reasons(item.nodeid)
            if gruende:
                rep.outcome = 'failed'
                rep.longrepr = '\n'.join([results.LEER_MELDUNG, *gruende])
    if rep.when == 'call' and rep.failed and item.get_closest_marker('warnung'):
        if not hasattr(rep, 'wasxfail'):
            rep.outcome = 'warnung'
    if rep.when == 'call':
        entry = _report.setdefault(item.nodeid, {})
        entry['nodeid'] = item.nodeid
        entry['outcome'] = 'xfailed' if hasattr(rep, 'wasxfail') and rep.skipped else rep.outcome
        entry['dauer_s'] = round(rep.duration, 3)
        entry['messwerte'] = results.records(item.nodeid)
        # Die Posen, in denen gemessen wurde. Ohne sie ist „0,2 mm Fuge" bei einer
        # bewegten Maschine nur die halbe Aussage.
        entry['posen'] = results.posen(item.nodeid)
        # Das Prüfbudget: woran gemessen wurde, was ausgelassen und was angenommen
        # wurde. Ohne das sieht ein Test, der die halbe Maschine übersprungen hat,
        # genauso grün aus wie einer, der alles angefasst hat.
        entry['budget'] = results.budget(item.nodeid)


def pytest_report_teststatus(report, config):
    if getattr(report, 'outcome', None) == 'warnung':
        return 'warnung', 'W', ('WARNUNG', {'yellow': True})
    if getattr(report, 'outcome', None) == 'unentschieden':
        return 'unentschieden', 'U', ('UNENTSCHIEDEN', {'yellow': True})


def pytest_sessionfinish(session, exitstatus):
    # „Unentschieden" ist kein Fehlschlag, aber erst recht kein Erfolg. pytest zählt
    # eigene Ausgänge nicht als Fehler, also setzt der Prüfstand den Rückgabewert
    # selbst -- sonst meldete ein Lauf ohne jedes Urteil Erfolg.
    if exitstatus == 0 and getattr(session.config, '_pruefstand_unentschieden', False):
        session.exitstatus = 1


def _budget_kopf(report: dict) -> dict:
    """Das Prüfbudget des ganzen Laufs in einer Zeile -- Summe über alle Tests."""
    koerper: dict[str, bool] = {}
    geprueft = uebersprungen = angenommen = 0
    gruende: dict[str, int] = {}
    for e in report.values():
        b = e.get('budget') or {}
        geprueft += len(b.get('geprueft', []))
        angenommen += len(b.get('angenommen', []))
        for k, hat_brep in (b.get('koerper') or {}).items():
            koerper[k] = bool(hat_brep) and koerper.get(k, True)
        for u in b.get('uebersprungen', []):
            n = int(u.get('anzahl', 1))
            uebersprungen += n
            art = str(u.get('was', 'sonst'))
            gruende[art] = gruende.get(art, 0) + n
    return {'geprueft': geprueft, 'uebersprungen': uebersprungen, 'angenommen': angenommen,
            'koerper': sorted(koerper), 'ohne_brep': sorted(k for k, v in koerper.items() if not v),
            'uebersprungen_nach_art': gruende}


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    project = getattr(config, '_pruefstand_project', None)
    if not _report:
        return
    lines = []
    for nodeid, e in _report.items():
        bits = []
        angeschnitten = False
        for m in e.get('messwerte', []):
            angeschnitten = angeschnitten or bool(m.get('fenster_schneidet_material'))
            keep = {k: v for k, v in m.items()
                    if k not in ('primitive', 'urteil_auf', 'fenster_schneidet_material',
                                 'obergrenze', 'obergrenze_felder')
                    and not isinstance(v, (list, dict)) and v is not None}
            # `≤` statt einer nackten Zahl, wo der Messung eine Ausnahme fehlt: „104
            # scharfe Kanten" und „höchstens 104" sind zwei verschiedene Aussagen.
            # Nur für die betroffenen Felder -- die Schwelle R4,2 bleibt R4,2.
            ober = set(m.get('obergrenze_felder') or ()) if m.get('obergrenze') else set()
            keep = {k: (f'≤{v}' if k in ober else v) for k, v in keep.items()}
            # Woher das Urteil kommt, gehört an den Messwert und nicht in eine Fußnote.
            woher = f"[{m['urteil_auf']}]" if m.get('urteil_auf') else ''
            bits.append(m['primitive'] + '(' + ', '.join(f'{k}={v}' for k, v in list(keep.items())[:3]) + ')' + woher)
        # `~` heißt: mindestens ein Messfenster lag mit seiner Wand im Material. Kein
        # Urteil -- aber der Messwert am Fensterrand könnte das Fenster selbst sein.
        marke = '~' if angeschnitten else ' '
        line = f"{marke}{e['outcome']:>8} {nodeid.split('::')[-1]} {' '.join(bits)}"
        lines.append(line[:121])
    terminalreporter.write_sep('-', 'pruefstand')
    for l in lines:
        terminalreporter.write_line(l)
    kopf = _budget_kopf(_report)
    terminalreporter.write_line(
        f"Budget: {kopf['geprueft']} Messungen an {len(kopf['koerper'])} Körpern "
        f"({len(kopf['ohne_brep'])} davon nur Netz), {kopf['uebersprungen']} übersprungen, "
        f"{kopf['angenommen']} Annahmen")
    if project is not None:
        out = project.review / 'pruefstand.json'
        out.write_text(json.dumps({'tests': list(_report.values()), 'budget': kopf,
                                   'erzeugt': time.strftime('%Y-%m-%dT%H:%M:%S')}, indent=2, default=str))
        terminalreporter.write_line(f'Bericht: {out}')
