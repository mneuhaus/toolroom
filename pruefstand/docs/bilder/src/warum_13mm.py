"""Bild fuer docs/warum.md: der R6d-Fehler neben der R1-Korrektur.

Schnitt in der Riemenebene (lokal X = -22) durch Zugbuegel, Riemen und Klemmbacken.
Links der gedruckte Stand R6d: die Backen sitzen 13,5 mm hinter dem Riemenruecken.
Rechts R1: die Zahnspitzen stehen im Riemenband.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from pruefstand import Machine, load_step

import _schnitt as S

X_CUT = -22.0
FARBE = {'bow': '#b8c6d9', 'jaw': '#f0a860', 'belt': '#3a3a3a'}


def main():
    m = Machine.load(S.MACHINE)
    loc = m.frame('local')

    alt_bow = S.section(S.local_mesh(m.body('R55'), loc), 0, X_CUT)
    alt_jaws = [S.section(S.local_mesh(m.body(k), loc), 0, X_CUT) for k in ('R06', 'R11')]
    belt = S.section(S.local_mesh(m.body('R15'), loc), 0, X_CUT)

    p = load_step(S.BELT_CLAMP / 'native/belt-clamp-r1-native.step')
    neu_bow = S.section(S.local_mesh(p.find('P03'), loc), 0, X_CUT)
    neu_jaws = [S.section(S.local_mesh(p.find(k), loc), 0, X_CUT)
                for k in ('Klemmbacke_upper', 'Klemmbacke_lower')]

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 5.6))
    for ax, (titel, bow, jaws, unter, namen) in zip(axes, [
        ('R6d — gebaut und gedruckt', alt_bow, alt_jaws,
         'Backen 13,5 mm hinter dem Riemen: der Riemen wird nie geklemmt',
         ('Zugbügel R55', 'Klemmbacken R06/R11')),
        ('R1 — vom Prüfstand abgenommen', neu_bow, neu_jaws,
         'Zahnspitzen 14,1 mm³ im Riemenband (overlap)',
         ('Zugbügel P03', 'Klemmbacken P04')),
    ]):
        S.draw(ax, bow, FARBE['bow'], label=namen[0])
        for j in jaws:
            S.draw(ax, j, FARBE['jaw'], label=namen[1] if j is jaws[0] else None, zorder=3)
        S.draw(ax, belt, FARBE['belt'], edgecolor='#000000', label='GT2-Riemen', zorder=4)
        ax.set_xlim(-16, 58)
        ax.set_ylim(-190, -140)
        ax.set_aspect('equal')
        S.sauber(ax, titel)
        ax.text(0.5, -0.20, unter, transform=ax.transAxes, ha='center', fontsize=9, color='#333333')
        ax.legend(loc='upper left', fontsize=8, framealpha=0.95)

    # Bemassung links: Zahnspitze der R1-Backe Y 21,6 -> Zahnspitze der alten Backe Y 35,1
    S.masspfeil(axes[0], (21.6, -158.0), (35.1, -158.0), '13,5 mm Luft', offset=(0, 4.0))
    axes[0].axvline(21.6, color='#b02020', lw=0.8, ls='--', zorder=1)
    axes[0].axvline(35.1, color='#b02020', lw=0.8, ls='--', zorder=1)
    axes[1].axvline(21.6, color='#2a7a2a', lw=0.8, ls='--', zorder=1)
    axes[1].annotate('Zahneingriff', xy=(21.8, -158.0), xytext=(34.0, -150.0), fontsize=9,
                     color='#2a7a2a', fontweight='bold',
                     arrowprops=dict(arrowstyle='->', color='#2a7a2a', lw=1.3))

    fig.suptitle('Riemenklemme R6d gegen R1 — Schnitt in der Riemenebene (lokal X = −22 mm)',
                 fontsize=12)
    fig.tight_layout(rect=(0, 0.06, 1, 0.94))
    out = S.BILDER / 'warum-13mm.png'
    fig.savefig(out, dpi=150)
    print('geschrieben:', out)


if __name__ == '__main__':
    main()
