import json

import numpy as np
import pytest
from build123d import export_stl

from pruefstand import Frame, Machine
from conftest import box


@pytest.fixture
def mini(tmp_path):
    local = tmp_path / 'local'
    local.mkdir()
    rows = []
    for key, at, moving in [('FIX', (0, 0, 0), False), ('MOV', (0, 0, 20), True)]:
        b = box(key, (10, 10, 10), at)
        export_stl(b.solid, str(local / f'{key}.stl'), tolerance=0.01, angular_tolerance=0.1)
        rows.append({'key': key, 'name': key, 'role': 'print', 'moving': moving,
                     'boundsMm': None, 'volumeMm3': 1000.0})
    (local / 'manifest.json').write_text(json.dumps(rows))
    out = tmp_path / 'machine'
    return Machine.from_manifest(local / 'manifest.json', out,
                                 frames={'local': Frame.identity()},
                                 motions={'hub': {'kind': 'translation', 'frame': 'local',
                                                  'axis': [0, 0, 1], 'range': [0, 130], 'default': 0}},
                                 name='mini', revision='R0')


def test_machine_json_und_laden(mini, tmp_path):
    p = tmp_path / 'machine' / 'machine.json'
    assert p.exists()
    m = Machine.load(p)
    assert len(m.keys()) == 2 and m.body('FIX').volume_mm3 == pytest.approx(1000, rel=1e-3)
    assert m.data['bodies'][0]['sha256']


def test_state_und_scene(mini):
    sc = mini.scene(hub=30)
    assert len(sc.fixed) == 1 and len(sc.moving) == 1
    mov = sc.moving[0]
    assert mov.bounds()[0][2] == pytest.approx(45.0, abs=1e-3)      # 15 + 30
    assert mini.scene().moving[0].bounds()[0][2] == pytest.approx(15.0, abs=1e-3)
    assert mini.scene(hub=30).only('FIX').keys() == ['FIX']
    assert mini.scene().without('FIX').keys() == ['MOV']


def test_range_wird_geprueft(mini):
    with pytest.raises(ValueError):
        mini.state(hub=200)
    with pytest.raises(ValueError):
        mini.state(quatsch=1)


def test_at_verschiebt_fremdkoerper(mini):
    fremd = box('X', (10, 10, 10), (0, 0, 20), moving=True)
    st = mini.state(hub=30)
    assert st.apply(fremd).bounds()[0][2] == pytest.approx(45.0, abs=1e-3)


@pytest.fixture
def dreh(tmp_path):
    """Maschine mit zwei unabhängigen Bewegungen: Hub schiebt MOV, Schwenk dreht nur FIX."""
    local = tmp_path / 'local'
    local.mkdir()
    rows = []
    for key, at, moving in [('FIX', (0, 0, 0), False), ('MOV', (0, 0, 20), True)]:
        b = box(key, (10, 10, 10), at)
        export_stl(b.solid, str(local / f'{key}.stl'), tolerance=0.01, angular_tolerance=0.1)
        rows.append({'key': key, 'name': key, 'role': 'print', 'moving': moving,
                     'boundsMm': None, 'volumeMm3': 1000.0})
    (local / 'manifest.json').write_text(json.dumps(rows))
    return Machine.from_manifest(local / 'manifest.json', tmp_path / 'machine',
                                 frames={'local': Frame.identity()},
                                 motions={'hub': {'kind': 'translation', 'frame': 'local',
                                                  'axis': [0, 0, 1], 'range': [0, 130], 'default': 0},
                                          'schwenk': {'kind': 'rotation', 'frame': 'world',
                                                      'axis': [1, 0, 0], 'origin': [0, 0, 50],
                                                      'range': [-135, 45], 'default': 0,
                                                      'applies_to': ['FIX']}},
                                 name='dreh', revision='R0')


def test_drehung_dreht_um_die_achse(dreh):
    """FIX (Mitte im Ursprung) um 90° um die X-Achse durch (0,0,50): Mitte nach (0,-50,50)."""
    b = dreh.state(schwenk=45).apply(dreh.body('FIX'))
    assert b.volume_mm3 == pytest.approx(1000, rel=1e-3)
    lo, hi = b.bounds()
    mitte = (np.asarray(lo) + np.asarray(hi)) / 2
    # Drehung um +45°: (0,0,0) -> (0, -sin45*(-50)... ) -- Abstand zur Achse bleibt 50
    assert np.linalg.norm(mitte[1:] - [0, 50]) == pytest.approx(50.0, abs=1e-3)
    assert mitte[0] == pytest.approx(0.0, abs=1e-3)


def test_motionen_wirken_nur_auf_ihre_koerper(dreh):
    """`applies_to` trennt die Bewegungen: der Hub lässt FIX stehen, der Schwenk MOV."""
    st = dreh.state(hub=30, schwenk=45)
    assert not np.allclose(st.matrix_for(dreh.body('FIX'))[:3, :3], np.eye(3))   # FIX dreht
    assert np.allclose(st.matrix_for(dreh.body('MOV'))[:3, :3], np.eye(3))       # MOV dreht nicht
    assert st.matrix_for(dreh.body('MOV'))[2, 3] == pytest.approx(30.0)


def test_displacement_verweigert_drehungen(dreh):
    """Eine Drehung ist keine Verschiebung -- lieber laut abbrechen als stillschweigend falsch."""
    with pytest.raises(NotImplementedError):
        dreh.state(schwenk=45).displacement()
    assert dreh.state(hub=30).displacement()[2] == pytest.approx(30.0)


def test_world_frame_gilt_auch_ungenannt(dreh):
    assert np.allclose(dreh.frame('world').matrix(), np.eye(4))


def test_pose_landet_im_bericht(mini):
    """Ein Messwert ohne Pose ist bei bewegter Maschine nur die halbe Aussage."""
    from pruefstand import gap, results
    from pruefstand import context
    context.set_test_id('test_pose_landet_im_bericht')
    try:
        results.clear()
        gap(box('X', (10, 10, 10)), mini.scene(hub=30))
        assert results.posen('test_pose_landet_im_bericht') == [{'hub': 30.0}]

        # Zweite Messung in derselben Pose: die Szene kommt aus dem Cache, `apply`
        # läuft nicht mehr -- die Pose muss trotzdem dranstehen, und nur einmal.
        gap(box('Y', (10, 10, 10)), mini.scene(hub=30))
        assert results.posen('test_pose_landet_im_bericht') == [{'hub': 30.0}]

        gap(box('Z', (10, 10, 10), moving=True), [box('F', (10, 10, 10), (0, 0, 40))],
            at=mini.state(hub=0))
        assert results.posen('test_pose_landet_im_bericht') == [{'hub': 30.0}, {'hub': 0.0}]
    finally:
        results.clear()
        context.set_test_id(None)
