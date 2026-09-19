"""Schematische Skizzen der fünf fertigen Primitive (docs/primitive.md).

Bewusst 2D und ohne echte Geometrie: jedes Bild soll in zwei Sekunden zeigen,
welche Zahl das Primitiv liefert. Die echten Beispiele stehen daneben in eigenen
Bildern (gap_real.py, overlap_real.py, ...).
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Polygon, Rectangle

import _schnitt as S

TEIL = '#8fb4dd'
MASCH = '#c9c9c9'
ROT = '#b02020'
GRUEN = '#2a7a2a'


def leinwand(titel, untertitel, xlim, ylim, figsize=(7.2, 4.2)):
    fig, ax = plt.subplots(figsize=figsize)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title(titel, fontsize=13, fontweight='bold', pad=14)
    ax.text(0.5, 1.005, untertitel, transform=ax.transAxes, ha='center', va='bottom',
            fontsize=9.5, color='#444444')
    return fig, ax


def speichern(fig, name):
    fig.tight_layout()
    out = S.BILDER / name
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print('geschrieben:', out)


def rect(ax, x, y, w, h, fc, label=None, hatch=None, ec='#222222', ls='-', lw=1.2, z=2):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=fc, edgecolor=ec, hatch=hatch,
                           linestyle=ls, linewidth=lw, zorder=z))
    if label:
        ax.text(x + w / 2, y + h / 2, label, ha='center', va='center', fontsize=10, zorder=z + 1)


def mass(ax, p0, p1, text, color=ROT, offset=(0, 0.9), fontsize=10):
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    ax.annotate('', xy=tuple(p1), xytext=tuple(p0),
                arrowprops=dict(arrowstyle='<->', color=color, lw=1.6, shrinkA=0, shrinkB=0), zorder=9)
    m = (p0 + p1) / 2 + np.asarray(offset, float)
    ax.text(m[0], m[1], text, color=color, fontsize=fontsize, fontweight='bold',
            ha='center', va='center', zorder=10,
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec=color, lw=1.0))


# -- gap ---------------------------------------------------------------------
def bild_gap():
    fig, ax = leinwand('gap(a, b)', 'kleinster Abstand zwischen zwei Körpermengen  ->  min_mm',
                       (-1, 21), (-1.5, 9))
    rect(ax, 1, 1, 8, 6, TEIL, 'a\nneues Teil')
    rect(ax, 12, 2, 8, 5, MASCH, 'b\nMaschine')
    ax.plot([9], [4.1], 'o', color=ROT, ms=6, zorder=9)
    ax.plot([12], [4.1], 'o', color=ROT, ms=6, zorder=9)
    mass(ax, (9, 4.1), (12, 4.1), 'min_mm = 1,0', offset=(0, 1.1))
    ax.text(10.5, 8.2, 'point_a / point_b\n(Welt, beide Berührpunkte)', ha='center', va='bottom',
            fontsize=8.5, color='#444444')
    ax.text(1, -1.2, 'within=Region  schneidet beide Netze vorher zu, ignore=Region nimmt eine Zone heraus',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-gap.png')


# -- overlap -----------------------------------------------------------------
def bild_overlap():
    fig, ax = leinwand('overlap(a, b)', 'gemeinsames Volumen  ->  volume_mm3 (exakt) oder collides (Netz)',
                       (-1, 21), (-1.5, 9))
    rect(ax, 2, 1, 8, 6, TEIL, None)
    rect(ax, 8, 2, 9, 5, MASCH, None)
    rect(ax, 8, 2, 2, 5, '#f7c6c6', None, hatch='///', ec=ROT, lw=1.6, z=4)
    ax.text(5, 4, 'a', ha='center', va='center', fontsize=11, zorder=6)
    ax.text(14, 4.5, 'b', ha='center', va='center', fontsize=11, zorder=6)
    ax.annotate('volume_mm3\ncollides = True', xy=(9, 5.4), xytext=(16.5, 8.4), fontsize=10,
                color=ROT, fontweight='bold', ha='center',
                arrowprops=dict(arrowstyle='->', color=ROT, lw=1.5))
    ax.text(0, -1.2, 'Berührung (Kontakttiefe <= 1e-4 mm) zählt als touching, nicht als collides',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-overlap.png')


# -- coverage ----------------------------------------------------------------
def bild_coverage():
    fig, ax = leinwand('coverage(by, region, direction)',
                       'Strahl je Abtastpunkt  ->  open = Zahl der Punkte ohne Treffer',
                       (-1, 21), (-2.5, 11))
    # Platte mit Lücke
    rect(ax, 1, 4, 8.5, 2, TEIL, None)
    rect(ax, 13, 4, 7, 2, TEIL, None)
    ax.text(5.2, 5, 'by (Teil)', ha='center', va='center', fontsize=9.5, zorder=5)
    ax.text(11.2, 5, 'Lücke', ha='center', va='center', fontsize=9, color=ROT)

    xs = np.arange(2.0, 20.0, 1.5)
    for x in xs:
        offen = 9.0 < x < 13.5
        farbe = ROT if offen else GRUEN
        ziel = 2.5 if offen else 6.0
        ax.annotate('', xy=(x, ziel), xytext=(x, 9.6),
                    arrowprops=dict(arrowstyle='->', color=farbe, lw=1.1, alpha=0.85), zorder=3)
        ax.plot([x], [3.0], 'o', color=farbe, ms=6, zorder=6)
    ax.text(0.2, 9.9, 'direction = (0, 0, −1), Start außerhalb aller Körper', fontsize=8.5,
            color='#444444')
    ax.text(0.2, 2.0, 'Abtastpunkte der Region (Region.points / Region.plane_grid)',
            fontsize=8.5, color='#444444')
    ax.text(0.2, 0.6, 'grün = getroffen (covered)      rot = offen (open) — hier 3 von 12',
            fontsize=9, color='#222222')
    ax.text(0.2, -1.5, 'map_png schreibt dieselbe Karte nach var/review/coverage-<test>.png',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-coverage.png')


# -- protrusion --------------------------------------------------------------
def bild_protrusion():
    fig, ax = leinwand('protrusion(part, volume)',
                       'Material in einem Sperrvolumen  ->  volume_mm3 (exakt) / hits (Netz)',
                       (-1, 21), (-2.0, 10))
    ax.add_patch(Rectangle((8, 1), 11, 7, facecolor='#fdf3d4', edgecolor='#c08a00',
                           linestyle='--', linewidth=1.8, zorder=1))
    ax.text(15.5, 7.1, 'volume = Region.box (Sperrvolumen)', fontsize=9, color='#8a6500',
            ha='center')
    pts = np.array([[1, 2.5], [9.8, 2.5], [9.8, 6.0], [1, 6.0]])
    ax.add_patch(Polygon(pts, closed=True, facecolor=TEIL, edgecolor='#222222', lw=1.2, zorder=2))
    ax.text(4.5, 4.2, 'part', ha='center', va='center', fontsize=11, zorder=3)
    ax.add_patch(Rectangle((8, 2.5), 1.8, 3.5, facecolor='#f7c6c6', edgecolor=ROT,
                           hatch='///', lw=1.6, zorder=4))
    ax.annotate('steht 1,8 mm vor\nvolume_mm3 > 0  ->  Fehler', xy=(9.0, 6.0), xytext=(14.0, 4.0),
                fontsize=10, color=ROT, fontweight='bold', ha='center',
                arrowprops=dict(arrowstyle='->', color=ROT, lw=1.5))
    ax.text(0, -1.3, 'typisch: "innen eben", Kabelkanal frei, Bauraum eines Zukaufteils',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-protrusion.png')


# -- same_as -----------------------------------------------------------------
def bild_same_as():
    fig, ax = leinwand('same_as(part, predecessor, region)',
                       'Region unverändert gegenüber dem Vorgänger  ->  max_deviation_mm',
                       (-1, 21), (-2.0, 10))
    alt = np.array([[1, 1], [18, 1], [18, 6], [10, 6], [10, 4.5], [1, 4.5]])
    neu = np.array([[1, 1], [18, 1], [18, 6], [10, 6], [10, 4.5], [6.5, 4.5],
                    [6.5, 6.6], [1, 6.6]])
    ax.add_patch(Polygon(alt, closed=True, facecolor=MASCH, edgecolor='#666666', lw=1.2, zorder=2))
    ax.add_patch(Polygon(neu, closed=True, facecolor='none', edgecolor='#1f5fa8', lw=2.2, zorder=4))
    ax.add_patch(Polygon(np.array([[1, 4.5], [6.5, 4.5], [6.5, 6.6], [1, 6.6]]), closed=True,
                         facecolor='#f7c6c6', edgecolor=ROT, hatch='///', lw=1.4, zorder=3))
    ax.text(13.5, 3.0, 'predecessor (grau)\npart (blaue Kontur)', fontsize=9.5, ha='center',
            color='#333333')
    ax.add_patch(Rectangle((8.5, 0.2), 11.0, 6.6, facecolor='none', edgecolor=GRUEN,
                           linestyle='--', lw=1.8, zorder=5))
    ax.text(14.0, 7.2, 'region = Messfenster: nur hier wird verglichen', fontsize=9.5,
            color=GRUEN, ha='center')
    ax.annotate('Änderung liegt außerhalb\nder Region -> bestanden',
                xy=(3.8, 5.5), xytext=(4.5, 8.7), fontsize=9.5, color=ROT, ha='center',
                arrowprops=dict(arrowstyle='->', color=ROT, lw=1.4))
    ax.text(0, -1.3, 'gemessen wird beidseitig: Oberflächenpunkte des einen zum nächsten Punkt auf dem anderen',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-same_as.png')


# -- Maschinenkontext --------------------------------------------------------
def bild_kontext():
    """Frame, Hub und Region in einem Bild (docs/konzepte.md)."""
    fig, ax = leinwand('Maschinenkontext',
                       'Weltachsen, gekippter Frame "local", Motion "hub", Region als Messfenster',
                       (-2, 23), (-3.2, 11), figsize=(8.6, 4.8))
    # Weltachsen
    ax.annotate('', xy=(3.6, 0.4), xytext=(0.4, 0.4),
                arrowprops=dict(arrowstyle='->', color='#444444', lw=1.4))
    ax.annotate('', xy=(0.4, 3.6), xytext=(0.4, 0.4),
                arrowprops=dict(arrowstyle='->', color='#444444', lw=1.4))
    ax.text(3.8, 0.4, 'Welt Y', fontsize=9, color='#444444', va='center')
    ax.text(0.4, 3.9, 'Welt Z', fontsize=9, color='#444444', ha='center')

    # gekippter lokaler Frame
    w = np.deg2rad(25.0)
    o = np.array([6.2, 2.2])
    ey = np.array([np.cos(w), -np.sin(w)])
    ez = np.array([np.sin(w), np.cos(w)])
    for e, name in ((ey, 'lokal Y'), (ez, 'lokal Z = Hubachse')):
        p = o + e * 3.2
        ax.annotate('', xy=tuple(p), xytext=tuple(o),
                    arrowprops=dict(arrowstyle='->', color='#1f5fa8', lw=2.0))
        ax.text(p[0] + 0.45 * e[0], p[1] + 0.45 * e[1], name, fontsize=9.5, ha='center',
                color='#1f5fa8', fontweight='bold')
    ax.plot([o[0]], [o[1]], 'o', color='#1f5fa8', ms=7, zorder=6)
    ax.text(o[0] - 0.45, o[1] + 0.2, 'Ursprung des Frames\n(hier: 25° gekippt, Welt-Z 203)',
            fontsize=8.5, color='#1f5fa8', ha='right', va='center')

    # feste Maschine, bewegter Körper, neues Teil
    rect(ax, 12.0, 1.2, 7.5, 1.4, MASCH, 'fest (moving = False)')
    rect(ax, 12.6, 5.2, 6.0, 1.3, '#e0d3ef', 'bewegt (moving = True)')
    rect(ax, 13.4, 7.2, 4.2, 1.3, TEIL, 'neues Teil')
    ax.annotate('', xy=(19.9, 6.7), xytext=(19.9, 3.1),
                arrowprops=dict(arrowstyle='<->', color='#6a3fa0', lw=1.8))
    ax.text(20.2, 4.9, 'hub\n0…130 mm', fontsize=9, color='#6a3fa0', fontweight='bold',
            va='center')

    ax.add_patch(Rectangle((12.9, 6.4), 5.2, 2.6, facecolor='none', edgecolor=GRUEN,
                           linestyle='--', lw=1.8, zorder=5))
    ax.text(15.5, 9.3, 'Region: Messfenster im Frame', fontsize=9.5, color=GRUEN, ha='center')

    ax.text(0.0, -1.2,
            'machine.scene(hub=65) verschiebt genau die Körper mit moving = True um 65 mm entlang lokal Z.\n'
            'Alle Koordinaten in Regionen sind lokale Koordinaten dieses Frames, nicht Weltkoordinaten.',
            fontsize=8.5, color='#444444')
    speichern(fig, 'schema-kontext.png')


if __name__ == '__main__':
    bild_kontext()
    bild_gap()
    bild_overlap()
    bild_coverage()
    bild_protrusion()
    bild_same_as()
