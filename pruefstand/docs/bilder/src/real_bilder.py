"""Bilder aus echter Geometrie der beiden Prüfprojekte (docs/primitive.md).

Jede Zahl im Bild stammt aus einem echten Aufruf des jeweiligen Primitivs, nicht
aus einer Skizze. Erzeugt:

    real-gap.png       Hopperboden T05 zur Hubplatte R10, 1,0 mm
    real-overlap.png   Zahnspitzen der Klemmbacke P04 im GT2-Riemen, 14,075 mm³
    real-coverage.png  220 Abtastpunkte der Bodenecken, R1 gegen R6d
    real-same_as.png   Messfenster hinter Y −33, Änderung liegt davor
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle

from pruefstand import Machine, Region, coverage, gap, overlap, load_step

import _schnitt as S

ROT = '#b02020'
GRUEN = '#2a7a2a'
TEIL = '#8fb4dd'
MASCH = '#c9c9c9'


def speichern(fig, name):
    out = S.BILDER / name
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('geschrieben:', out)


def schatten(ax, mesh_local, achsen, facecolor, alpha=1.0, zorder=2, label=None):
    """Umriss (Schattenwurf) eines Netzes: alle Dreiecke flach in zwei Achsen projiziert."""
    from matplotlib.collections import PolyCollection
    v = np.asarray(mesh_local.vertices, dtype=float)[:, achsen]
    tri = v[np.asarray(mesh_local.faces)]
    pc = PolyCollection(tri, facecolors=facecolor, edgecolors='none', alpha=alpha,
                        zorder=zorder, label=label)
    ax.add_collection(pc)
    return pc


def hopper():
    m = Machine.load(S.MACHINE)
    loc = m.frame('local')
    p = load_step(S.HOPPER / 'native/hopper-floor-r1-native.step')
    return m, loc, p.one(key='T05', moving=False)


# -- gap ---------------------------------------------------------------------
def bild_gap(m, loc, t05):
    r = gap(t05, m.scene(hub=0).only('R10', 'R39', 'R77'))
    print('gap:', r)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    S.draw(ax, S.section(S.local_mesh(t05, loc), 0, 0.0), TEIL,
           label='Hopperboden T05 (neues Teil)')
    S.draw(ax, S.section(S.local_mesh(m.body('R10'), loc), 0, 0.0), MASCH,
           label='Hubplatte R10 (Maschine, Hub 0)')
    ax.annotate('', xy=(-4.8, -2.0), xytext=(-5.8, -2.0),
                arrowprops=dict(arrowstyle='<->', color=ROT, lw=1.4, shrinkA=0, shrinkB=0),
                zorder=10)
    ax.annotate(f'min_mm = {r.min_mm:.5f}', xy=(-5.3, -2.0), xytext=(-9.5, -8.0),
                color=ROT, fontsize=11, fontweight='bold', ha='center', zorder=11,
                arrowprops=dict(arrowstyle='->', color=ROT, lw=1.2),
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=ROT, lw=0.9))
    ax.set_xlim(-15, 1)
    ax.set_ylim(-11, 3)
    ax.set_aspect('equal')
    S.sauber(ax, 'gap(t05, machine.scene(hub=0).only("R10", "R39", "R77"))')
    ax.legend(loc='lower left', fontsize=8)
    fig.text(0.5, 0.04,
             'Schnitt bei lokal X = 0. Vorderkante des Bodens bei Y −5,8, Wagenkante bei Y −4,8.\n'
             'Derselbe Wert wird für Hub 0, 65 und 130 geprüft.',
             ha='center', fontsize=9, color='#333333')
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    speichern(fig, 'real-gap.png')


# -- overlap -----------------------------------------------------------------
def bild_overlap():
    m = Machine.load(S.MACHINE)
    loc = m.frame('local')
    p = load_step(S.BELT_CLAMP / 'native/belt-clamp-r1-native.step')
    riemen = p.find('open_belt')
    backe = p.find('Klemmbacke_upper')

    r = overlap(riemen, backe)
    print('overlap:', r)

    fig, ax = plt.subplots(figsize=(8.0, 5.0))
    S.draw(ax, S.section(S.local_mesh(riemen, loc), 0, -22.0), '#3a3a3a',
           edgecolor='#000000', label='GT2-Riemen (Zukaufteil im STEP)', zorder=3)
    S.draw(ax, S.section(S.local_mesh(backe, loc), 0, -22.0), '#f0a860',
           label='Klemmbacke P04 (neues Teil)', zorder=4)
    ax.axvspan(20.94, 22.30, color=ROT, alpha=0.18, zorder=6)
    ax.annotate(f'volume_mm3 = {r.volume_mm3:.5f}\ncollides = True, exact = True',
                xy=(21.9, -154.4), xytext=(28.0, -151.0), fontsize=10, color=ROT,
                fontweight='bold', ha='center', zorder=8,
                arrowprops=dict(arrowstyle='->', color=ROT, lw=1.5))
    ax.set_xlim(16, 34)
    ax.set_ylim(-167, -148)
    ax.set_aspect('equal')
    S.sauber(ax, 'overlap(riemen, klemmbacke) — Zahnspitzen im Riemenband')
    ax.legend(loc='lower left', fontsize=8)
    fig.text(0.5, 0.04,
             'Schnitt bei lokal X = −22. Das Riemenband liegt zwischen Y 20,94 und 22,30 (rot hinterlegt).\n'
             'Gewollte Durchdringung: ohne sie greift die Klemmung nicht. Der Test verlangt 13 bis 15 mm³.',
             ha='center', fontsize=9, color='#333333')
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    speichern(fig, 'real-overlap.png')


# -- coverage ----------------------------------------------------------------
def eckpunkte():
    q = 0.122784560902905
    pts = []
    for sgn in (-1, 1):
        for x in np.arange(79, 112, 2.0):
            for y in np.arange(-21.5, -6, 1.5):
                if x > 89.9 and y > -17.0:
                    continue
                pts.append([sgn * x, y, (y + 6.1) * q - 2.0])
    return np.array(pts)


def bild_coverage(m, loc, t05):
    pts = eckpunkte()
    region = Region.points(loc, pts)
    ergebnis = {}
    for name, koerper in (('R1', t05), ('R6d', m.body('T05'))):
        r = coverage(by=[koerper], region=region, direction=(0, 0, -1))
        ergebnis[name] = r
        print(f'coverage {name}:', r)

    fig, axes = plt.subplots(2, 1, figsize=(9.8, 4.4))
    for ax, name in zip(axes, ('R1', 'R6d')):
        r = ergebnis[name]
        koerper = t05 if name == 'R1' else m.body('T05')
        schatten(ax, S.local_mesh(koerper, loc), [0, 1], '#dce6f2', zorder=1,
                 label='Bodenumriss von oben')
        offen = np.asarray(r.open_points, dtype=float) if len(r.open_points) else np.zeros((0, 3))
        mask = np.zeros(len(pts), dtype=bool)
        if len(offen):
            for o in offen:
                d = np.linalg.norm(loc.to_local(o.reshape(1, 3)) - pts, axis=1)
                mask[int(np.argmin(d))] = True
        ax.plot(pts[~mask, 0], pts[~mask, 1], 'o', color=GRUEN, ms=3.2,
                label=f'covered = {r.covered}')
        if mask.any():
            ax.plot(pts[mask, 0], pts[mask, 1], 'o', color=ROT, ms=3.2,
                    label=f'open = {r.open}')
        ax.set_xlim(-124, 124)
        ax.set_ylim(-26, 0)
        ax.set_aspect('equal')
        S.sauber(ax, f'{name}: total = {r.total}, covered = {r.covered}, open = {r.open}',
                 xlabel='lokal X  [mm]' if name == 'R6d' else '',
                 ylabel='lokal Y  [mm]')
        ax.legend(loc='upper center', fontsize=8, ncol=3, framealpha=0.95)

    fig.suptitle('coverage(by=[boden], region=Region.points(...), direction=(0, 0, −1))',
                 fontsize=12)
    fig.text(0.5, 0.03,
             'Je Abtastpunkt läuft ein Strahl nach unten. Rot = kein Treffer, dort ist der Boden offen.\n'
             'R6d hatte an beiden Ecken die Fase aus R5; R1 schließt sie.',
             ha='center', fontsize=9, color='#333333')
    fig.tight_layout(rect=(0, 0.11, 1, 0.95))
    speichern(fig, 'real-coverage.png')


# -- same_as -----------------------------------------------------------------
def bild_same_as(m, loc, t05):
    from pruefstand import same_as
    hinten = Region.box(loc, (-130, -130, -30), (130, -33, 30))
    r = same_as(t05, m.body('T05'), hinten)
    print('same_as:', r)

    fig, ax = plt.subplots(figsize=(9.5, 6.4))
    schatten(ax, S.local_mesh(t05, loc), [0, 1], '#5f8fc4', alpha=1.0, zorder=2,
             label='T05 R1 (part), Umriss von oben')
    schatten(ax, S.local_mesh(m.body('T05'), loc), [0, 1], '#cccccc', alpha=1.0, zorder=3,
             label='T05 aus R6d (predecessor)')
    ax.add_patch(Rectangle((-130, -130), 260, 97, facecolor='none', edgecolor=GRUEN,
                           linestyle='--', lw=2.0, zorder=5))
    ax.text(0, -36, 'region = Region.box(...): alles hinter lokal Y −33', color=GRUEN,
            fontsize=10, ha='center', va='top', fontweight='bold', zorder=6,
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=GRUEN, lw=0.8))
    ax.annotate('blau sichtbar = Änderung gegenüber R6d\n(geschlossene Ecken, vor der Region)',
                xy=(-104, -14), xytext=(-30, -58), fontsize=9.5, color=ROT,
                ha='center', zorder=7, arrowprops=dict(arrowstyle='->', color=ROT, lw=1.4))
    ax.set_xlim(-135, 135)
    ax.set_ylim(-134, 4)
    ax.set_aspect('equal')
    S.sauber(ax, f'same_as(t05, t05_alt, hinten) — max_deviation_mm = {r.max_deviation_mm:.5f}',
             xlabel='lokal X  [mm]', ylabel='lokal Y  [mm]')
    ax.legend(loc='lower right', fontsize=8)
    fig.text(0.5, 0.04,
             f'{r.samples} Punktpaare, größte Abweichung {r.max_deviation_mm:.5f} mm.\n'
             'Draufsicht, Umriss beider Körper übereinander.',
             ha='center', fontsize=9, color='#333333')
    fig.tight_layout(rect=(0, 0.14, 1, 1))
    speichern(fig, 'real-same_as.png')


if __name__ == '__main__':
    m, loc, t05 = hopper()
    bild_gap(m, loc, t05)
    bild_coverage(m, loc, t05)
    bild_same_as(m, loc, t05)
    bild_overlap()
