import math

import numpy as np
import pytest

from pruefstand import Frame, Region


def test_frame_hin_und_zurueck():
    c, s = math.cos(math.radians(25)), math.sin(math.radians(25))
    f = Frame([[1, 0, 0], [0, c, s], [0, -s, c]], (0, 0, 203))
    p = np.array([[1.0, 2.0, 3.0], [-4.0, 5.0, 6.0]])
    assert np.allclose(f.to_local(f.to_world(p)), p)
    assert np.allclose(f.to_world([0, 0, 0]), [0, 0, 203])
    assert np.allclose(f.matrix()[:3, 3], [0, 0, 203])


def test_frame_rot_z():
    f = Frame.rot_z(90)
    assert np.allclose(f.to_world([1, 0, 0]), [0, 1, 0], atol=1e-9)


def test_richtung_hin_und_zurueck():
    """Eine Richtung wird gedreht, nicht verschoben -- sonst wird eine Normale ein Ort."""
    f = Frame.rot_z(35, (10, -20, 203))
    v = np.array([0.0, 0.0, 1.0])
    assert np.allclose(f.direction_to_local(f.direction_to_world(v)), v)
    assert np.allclose(f.direction_to_world(f.direction_to_local(v)), v)
    # Der Unterschied zu to_local: die Verschiebung bleibt außen vor.
    assert np.allclose(f.direction_to_local([1, 0, 0]), f.rotation.T @ np.array([1.0, 0, 0]))
    assert not np.allclose(f.direction_to_local([1, 0, 0]), f.to_local([1, 0, 0]))


def test_region_box_contains_und_solid():
    r = Region.box(Frame.identity(), (-1, -1, -1), (1, 1, 1))
    assert list(r.contains([[0, 0, 0], [2, 0, 0]])) == [True, False]
    assert abs(r.solid().volume - 8.0) < 1e-6


def test_region_plane_grid():
    r = Region.plane_grid(Frame.identity(), 'xy', u=(0, 2, 1), v=(0, 1, 1), w=5.0)
    pts = r.sample_points()
    assert len(pts) == 6 and np.allclose(pts[:, 2], 5.0)


def test_zylinder_enthaelt_und_schneidet():
    """Zylinderfenster: Punkte nach Radius und Achslage, Mesh am Mantel beschnitten."""
    import trimesh
    from pruefstand import Frame, Region
    z = Region.cylinder(Frame.identity(), (0, 0, 0), (0, 0, 1), radius=10.0, length=20.0)
    drin = z.contains([(0, 0, 10), (9.9, 0, 5), (10.1, 0, 5), (0, 0, -0.1), (0, 0, 20.1)])
    assert list(drin) == [True, True, False, False, False]

    # Platte 60x60x2 mittig auf der Achse: im Fenster bleibt die Kreisscheibe.
    platte = trimesh.creation.box(extents=(60, 60, 2))
    platte.apply_translation((0, 0, 10))
    teil = z.crop(platte)
    lo, hi = teil.bounds
    assert hi[0] - lo[0] == pytest.approx(20.0, abs=z.meta['rand_unschaerfe_mm'])
    assert hi[1] - lo[1] == pytest.approx(20.0, abs=z.meta['rand_unschaerfe_mm'])
    ecken = np.linalg.norm(teil.vertices[:, :2], axis=1)
    assert ecken.max() <= 10.0 + 1e-9        # nichts außerhalb des Mantels


def test_zylinder_schneidet_die_deckel_exakt():
    """Die Stirnflächen sind Ebenen -- die schneidet der Halbraumschnitt scharf."""
    import trimesh
    from pruefstand import Frame, Region
    stab = trimesh.creation.box(extents=(4, 4, 100))
    z = Region.cylinder(Frame.identity(), (0, 0, -10), (0, 0, 1), radius=20.0, length=30.0)
    teil = z.crop(stab)
    lo, hi = teil.bounds
    assert lo[2] == pytest.approx(-10.0, abs=1e-9) and hi[2] == pytest.approx(20.0, abs=1e-9)


def test_zylinder_negative_laenge_zeigt_zurueck():
    from pruefstand import Frame, Region
    z = Region.cylinder(Frame.identity(), (0, 0, 0), (0, 0, 1), radius=5.0, length=-8.0)
    assert z.contains([(0, 0, -4)])[0] and not z.contains([(0, 0, 4)])[0]


def test_zylinder_solid_hat_das_richtige_volumen():
    from pruefstand import Frame, Region
    z = Region.cylinder(Frame.identity(), (1, 2, 3), (0, 1, 0), radius=6.0, length=10.0)
    s = z.solid()
    assert s.volume == pytest.approx(np.pi * 36 * 10, rel=1e-3)
    lo = s.bounding_box().min
    assert lo.Y == pytest.approx(2.0, abs=1e-6)


def test_zylinder_als_ring():
    """`inner_radius` schneidet die Mitte aus -- Lochkreis messen ohne die Nabe."""
    import trimesh
    from pruefstand import Frame, Region
    z = Region.cylinder(Frame.identity(), (0, 0, 0), (0, 0, 1), radius=12.0, length=4.0,
                        inner_radius=8.0)
    assert list(z.contains([(10, 0, 2), (4, 0, 2), (12.5, 0, 2)])) == [True, False, False]
    assert z.solid().volume == pytest.approx(np.pi * (144 - 64) * 4, rel=1e-3)
    platte = trimesh.creation.box(extents=(60, 60, 4))
    platte.apply_translation((0, 0, 2))
    r = np.linalg.norm(z.crop(platte).vertices[:, :2], axis=1)
    assert r.max() <= 12.0 + 1e-9 and r.min() >= 8.0 - 1e-9
