# Etappe 5 — Bericht für Marc und Fable

Stand 18.09.2026. Auftrag: die sechs Werkzeuglücken aus `r7-analyse-bericht.md`,
Abschnitt 8, schließen, dazu der Splitter-Befund aus `var/etappe4-bericht.md`. Kein
Onshape-Aufruf, kein `python3`, kein Git, keine `_v2`-Datei. Alles offline auf STEP +
`machine.json`.

## Testsummen (letzter tatsächlicher Lauf, nicht geschätzt)

```
uv run pytest tests -q                       (toolroom/pruefstand)
  298 passed, 4 warnings in 36.63s           vorher: 283 passed                    exit 0

uv run --project .../pruefstand pytest spec/test_tray_r1.py -q
  73 passed, 1 xfailed, 1 warnung,
  4 warnings in 39.10s                       unverändert                           exit 0

uv run --project .../pruefstand pytest spec/test_hopper_floor.py -q
  27 passed, 2 xfailed, 3 warnung,
  4 warnings in 9.48s                        unverändert                           exit 0

uv run --project .../pruefstand pytest spec -q            (rocking-photo-tray-r7)
  220 passed, 7 xfailed, 50 warnung,
  4 warnings in 107.17s                      vorher: 172 passed, 8 xfailed, 52 w   exit 0
    davon spec/test_r6d_bestand.py           114 passed, 5 xfailed, 46 warnung
          (vorher 67 passed, 5 xfailed, 48 warnung)
    davon test_tray_r2 + test_hopper_floor_r2  106 passed, 2 xfailed, 4 warnung
          (vorher 105 passed, 3 xfailed, 4 warnung)
```

Zur Sicherheit mitgelaufen, weil dieselbe Bibliothek: Riemenklemme R1 unverändert
`13 passed, 2 xfailed, 4 warnings in 2.71s`.

**Ein `xfail` ist entfallen**, weil die Regel jetzt stimmt: `test_die_wanne_hat_keine_splitter`
(Tray R2). Die 16 Treffer waren die tangentialen Übergänge der acht neuen Randrundungen.
Sie sind nicht wegtoleriert, sondern richtig einsortiert — der Test daneben
(`test_die_randrundungen_bleiben_als_uebergaenge_sichtbar`) zählt dieselben 16 weiter und
fiele, wenn eine Rundung verschwände.

**Die anderen sieben `xfail` habe ich einzeln nachgerechnet**, keiner davon hängt an einer
der berichtigten Regeln:

| `xfail` | rot wegen | von Etappe 5 berührt? |
|---|---|---|
| T41L / T41R Randband | 14 bzw. 11 Konturabsätze (`umriss` + `banddicke`) | nur die Sortierung; die Zahlen 38/42 und 14/11 sind unverändert |
| T40 Gleichteilprobe | 26 gegen 17 Absätze, 12 nur links | nein, `absatz` zählt wie vorher |
| T02 Splitter | 96 Kanten < 0,42 mm + 32 Flächen < 1 mm² | nein — T02 hatte **null** unverschmolzene Nachbarn, vorher wie nachher |
| Hopperboden 0,371 mm (2×) | einspringende Rahmenecke | nein, `gap.min_mm` unverändert (0,37128 mm) |
| Hopperboden Ecken R6d (`coverage`) | Lücke neben den Wagen | nein |

## Was fertig ist

### 1. `gap`: Formschluss ist keine Durchdringung

`penetrating` wird **nachgerechnet**, nie aus `distance() == 0` geschlossen — Berührung und
Durchdringung liefern dort denselben Wert.

* beide Körper mit Solid und ohne `within`/`ignore` → exakter Schnitt > 0 mm³
  (`penetration_auf='brep'`),
* sonst Netz → größte Tiefe, mit der Stützpunkte **und Facettenmitten** des einen im
  anderen liegen, Schwelle `DURCHDRINGUNG_MM = 0,01 mm` (`penetration_auf='mesh'`,
  `durchdringung_mm` trägt den Wert),
* offenes Netz → `penetration_auf='unentschieden'`, `penetrating` bleibt `False`, und das
  steht als `uebersprungen` im Budget.

`urteil_auf` bleibt ehrlich `'mesh'`: der **Abstand** kommt weiter aus dem Kollisionskern.
Dass `penetrating` exakt sein kann, steht daneben in `penetration_auf` — ein exakter
Nebenwert macht ein abgetastetes Urteil nicht exakt.

| Prüfkörper | Ergebnis |
|---|---|
| zwei Quader bündig (Fläche an Fläche) | `min_mm 0,0`, **`penetrating=False`**, `brep`; `overlap` daneben 0,0 mm³ |
| zwei Quader 0,05 mm ineinander | `penetrating=True`, `brep` |
| zwei Quader 5 mm ineinander | `penetrating=True`, `brep` (Altbestand, unverändert) |
| dieselben als STL | bündig `False` / 0,05 mm `True`, `mesh`, `durchdringung_mm 0,05` |
| **T40L↔T41L, T40R↔T41R** (R6d, alle 12 Posen) | `min_mm 0,0`, **kein** `penetrating` mehr |

### 2. `kerbe`: Ankerradius aus der Spaltbreite

Je Zone gilt `anker = max(anker_mm, anker_faktor · spalt)`, Vorgaben 2,5 mm und **3,0**.
Beide je Aufruf und je Teil in `spec/form.yaml` überschreibbar (`anker_mm:`,
`anker_faktor:`); Reihenfolge Aufruf > Pflegedatei > Hausregel. Der angewandte Radius steht
an jeder Zone (`anker_mm`), damit nichts unsichtbar wirkt.

**Abweichung vom Auftrag, mit Messung begründet:** der Plan nennt `max(2,5; 2·spalt)`. Das
erklärt **keine einzige** der 13 Rahmenfugen — sie sind 1,45 mm breit (2 × 1,45 = 2,90 mm),
ihre Partner liegen bei 3,7 bis 4,0 mm. Gemessen über die fünf vertieften Teile:

| Faktor | erklärt zusätzlich | erste Stelle, die fälschlich mitginge |
|---|---|---|
| 2,0 | 0 von 13 | — |
| **3,0** | **genau die 13** (Grenze 4,35 mm) | keine |
| 4,0 | die 13 + die 95-mm-Nut an T41R (Partner HORN0 in 5,53 mm) | ja |

Zwischen 4,0 mm (Rahmenfuge) und 5,53 mm (echte Nut) liegt nichts — die Trennung ist nicht
knapp, sondern deutlich. Wirkung auf die unerklärten Zonen:

| Teil | vorher | nachher | was wegfiel |
|---|---|---|---|
| T41L | 11 | **6** | 5 Sitze mit Partner R59/T40L in 3,7–4,0 mm |
| T41R | 7 | **3** | 4 dito |
| T40L | 4 | **2** | 2 mit Partner R62 in 3,7 mm |
| T40R | 4 | **2** | 2 dito |
| T02 | 8 | 8 | nichts — alle Partner ab 6,12 mm, echte Nuten |

Weiterhin gemeldet, wie verlangt: die **0,341 mm** über 12,00 mm bei ±118,6 / 152,7 / 264,0
(im STEP wiedergefunden; Fables Sonde nannte 0,29 mm bei Z 265 am STL). Ihr Anker bleibt bei
2,5 mm, denn 3 × 0,341 = 1,02 mm — schmale Nuten bekommen nichts geschenkt. Ebenso die
0,353-mm-Nut an ±113,0 / 42,7 / 338,6 und die 1,0-mm-Kerbe über 27,25 mm bei −112,6 / 135,2.

### 3. `unverrundet`: Obergrenze kennzeichnen, `spec/teile.yaml` auswerten

Ohne Druckpose und ohne Kontext ist jede Zahl zu groß — Bettkanten und Fugenkanten werden
nie verrundet, zählen aber mit. Das Ergebnis sagt es jetzt selbst:

* `result.obergrenze = True`, dazu `ausnahmen = {bettseite, fugenkanten, griffkanten}`,
* im JSON `obergrenze` samt `obergrenze_felder`,
* im Terminalbericht `unverrundet(anzahl=≤104, gesamt_mm=≤2461.4, radius_mm=4.2)` — das `≤`
  steht nur an Zählung und Summe; eine Schwelle ist keine Obergrenze.

Neue Pflegedatei `spec/teile.yaml`, Schema `pruefstand.teile/1`:

```yaml
schema: pruefstand.teile/1
teile:
  - key: T41L
    pose: {rotate: [0, 90, 0]}       # Druckpose, wie printing.pose_matrix sie nimmt
    auflage: {normale: [0, 0, -1]}   # Richtung ZUM Bett -- oder region: {frame, von, bis}
    griffkanten: nein                # ja | nein
    radius_mm: 1.0                   # optional: Schwelle je Teil
```

`griffkanten: nein` setzt die Schwelle auf den Kantenbruch `KANTENBRUCH_MM = 1,0` statt
R4,2; `radius_mm` schlägt beides. **Die Zählung ändert die Schwelle nicht** — eine scharfe
Kante ist scharf, gleich welcher Radius verlangt ist. Was sich ändert, ist die Schwelle im
Ergebnis und im Klartext der Meldung. (Eine bereits gebrochene Kante hat 135°, keine 90°,
und fällt ohnehin aus dem Knickfenster.)

Fugenkanten kommen aus `kontext=` (Scene, Liste von Szenen, Bodies): liegt ein Nachbarkörper
näher als `fuge_mm` = 1,0 mm — das Nahfeld aus dem HANDOFF —, stößt dort ein anderes Teil an.

| Prüfkörper | Ergebnis |
|---|---|
| Quader 20³ auf dem Bett, ohne Angaben | 12 Kanten, `obergrenze=True` |
| derselbe mit `auflage: {normale: [0,0,-1]}` und Nachbarn in 0,1 mm | **5** Kanten, `obergrenze=False`, Schwelle 1,0 mm |
| derselbe mit `auflage: {region: …}` | 8 Kanten (nur Bettseite ausgenommen) |

Für die 15 R6d-Teile gibt es **keine** `teile.yaml`: ihre Druckposen sind nicht dokumentiert,
und eine erfundene Pose wäre eine erfundene Zahl. Alle Spalten „unverrundet" im
R7-Bestand sind deshalb weiterhin Obergrenzen — jetzt aber ausdrücklich als solche
markiert, ein eigener Test hält es je Teil fest.

### 4. `splitter`: tangentiale Übergänge sind kein Splitter

Unverschmolzen heißt jetzt: Knick < 0,5° zwischen zwei **verschiedenen und ungekrümmten**
Flächen. Geht der Übergang auf einen Zylinder oder Torus, ist er das Merkmal selbst und
landet in `rundungsuebergaenge` (mit `flaechentypen`), nicht in `unverschmolzen`.

Nachgezählt über alle 15 BRep-Teile: **alle 145** früheren Treffer hatten mindestens eine
Zylinderfläche als Nachbarn — C07 10, R55 60, R59 7, R62 9, T01 12, T40L 7, T40R 4, T41L 20,
T41R 16. Nach der Berichtigung meldet **kein einziges Teil** noch einen unverschmolzenen
Nachbarn; ein eigener Test hält genau das fest, damit ein echter Fall (zwei Ebenen) auffiele.

Der echte Fall ist geprüft: zwei Quader, mit dem rohen `BRepAlgoAPI_Fuse` **ohne**
Aufräumen vereinigt (build123ds `+` legt gleichliegende Ebenen selbst zusammen), ergeben
zehn statt acht Flächen und vier Kanten Ebene/Ebene mit Knick 0° — die werden weiter
gemeldet.

Wirkung auf die Bestandszahlen (Spalte `splitter`, Summe der drei Listen):

| Teil | vorher | nachher | Rest |
|---|---|---|---|
| C07 | 10 | **0** | 10 Fillet-Übergänge |
| R55 | 163 | **103** | 103 Kurzkanten, echt |
| R59 | 32 | **25** | 19 Kanten + 6 Flächen |
| R62 | 17 | **8** | 6 + 2 |
| T01 | 12 | **0** | 12 Übergänge |
| T40L / T40R | 31 / 19 | **24 / 15** | Kurzkanten, echt |
| T41L / T41R | 45 / 41 | **25 / 25** | 20 Kanten + 5 Flächen je Seite, echt |
| T02 | 128 | 128 | unverändert — dort war nie ein Übergang dabei |

### 5. `absatz`: Feld `sorte`

`sorte` ∈ `umriss` / `banddicke` / `pad`, dazu `sorten` (Zählung) und `achse`. Verfahren wie
in `rocking-photo-tray-r7/src/t41_details.py`: die Normalen der beiden Wände und der Stufe,
bezogen auf die Plattenachse. Neu und nötig für die Verallgemeinerung: die Achse kommt aus
der **dünnsten Hüllrichtung** des Körpers (`form.plattenachse`) statt aus einem hart
verdrahteten X. Sie ist per `achse=` überschreibbar und steht in den Annahmen.

Gegenprobe an T41: die Regel liefert **1 umriss + 13 banddicke** (T41L) und
**1 + 10** (T41R) — Zeichen für Zeichen die Zahlen der Handrechnung (14 bzw. 11). Die
Plattenachse wird für beide korrekt als X erkannt. Der Test im R7-Projekt rechnet die
Sorten deshalb nicht mehr selbst aus, sondern liest `sorte`.

Prüfkörper (Platte 60 × 40 × 4, dünn in Z):

| Körper | Ergebnis |
|---|---|
| Block 1,5 mm hoch auf der großen Fläche | 4 × `pad` |
| Stirnseite unten 1 mm vorstehend | 1 × `banddicke` (1,0 mm über 40 mm) + 1 × `pad` (Unterseite) |
| Stirnseite über die volle Dicke vorstehend | 1 × `umriss` |

### 6. `Frame.direction_to_local`

Gegenstück zu `direction_to_world`: dreht, ohne zu verschieben. `t41_details.py` benutzt es
jetzt statt `frame.rotation.T @ v`.

### Doku

- `SPEC.md`: Verträge für `gap.penetrating` / `penetration_auf` / `durchdringung_mm`,
  `absatz(achse=…)` + `sorte`, `kerbe(anker_mm, anker_faktor)`, `unverrundet(teil, kontext,
  fuge_mm)` + Obergrenze, `splitter` mit `rundungsuebergaenge`, neuer Abschnitt zu
  `spec/teile.yaml`, `Frame.direction_to_local`, Paketliste.
- `docs/primitive.md`: gap-Rückgabetabelle und der Abschnitt „Berührung ist keine
  Kollision"; im Formabschnitt die drei Sorten mit den T41-Zahlen, der wachsende
  Ankerradius, die Obergrenze und beide Pflegedateien.
- `docs/konzepte.md`, Kapitel 7: Anker aus der Spaltbreite, die drei Sorten, „ein
  tangentialer Fillet ist kein Splitter", „was der Prüfstand nicht weiß, sagt er als
  Obergrenze".
- `docs/fallstricke.md`: drei neue Einträge (Abstand 0 als Kollisionsbeleg, Fillet gegen
  unverschmolzene Ebene samt Bauanleitung für den Prüfkörper, Bettebene je Kante).
- `docs/README.md`: Etappe-5-Liste und neue Projektsummen.

## Entscheidungen zwischen zwei Lesarten

1. **Ankerfaktor 3 statt 2.** Siehe oben: Faktor 2 erfüllt die Vorgabe „aus der Spaltbreite
   ableiten", aber nicht die Vorgabe „die 13 Rahmenfugen müssen erklärt werden". Faktor 3
   erfüllt beide und trennt sauber (4,0 gegen 5,53 mm). Das ist keine gelockerte Toleranz —
   der Anker ist kein Maß am Teil, sondern die Frage, ob jemand daneben steht; und er steht
   je Zone im Bericht.
2. **Netz-Durchdringung über Stützpunkte *und* Facettenmitten.** Nur die Stützpunkte zu
   prüfen misst bei zwei Quadern null: die einzigen eingedrungenen Punkte sind Ecken, und
   die liegen auf den Seitenflächen des Gegenkörpers. `fcl.penetration_depth` ist als Maß
   unbrauchbar — für koinzidente Netze liefert es die volle Körpertiefe (10,0 mm bei zwei
   bündigen 10er-Würfeln).
3. **Offene Netze bekommen kein Urteil.** STL-Körper werden mit `process=False` geladen,
   damit ist rohes `is_watertight` immer falsch; geprüft wird an einer Kopie mit
   zusammengelegten Stützpunkten (einmal je Netz, gecacht). Bleibt sie offen, ist „innen"
   nicht definiert, und `penetrating` sagt nichts, statt etwas zu erfinden.
4. **`obergrenze` gilt nur für Zählungen.** `radius_mm=≤4,2` wäre schlicht falsch — die
   Schwelle ist keine Obergrenze, nur weil der Messung eine Ausnahme fehlt. Deshalb nennt
   das Ergebnis die betroffenen Felder (`anzahl`, `gesamt_mm`), und das Plugin markiert nur
   diese.
5. **`teile.yaml` neben `druck.yaml` statt hineingebaut.** `druck.yaml`
   (`pruefstand.druck/1`) trägt Profil und Lastabschnitte für `print_pose` und `stability`.
   Die Formregeln brauchen davon nichts außer der Pose, aber zusätzlich Auflage und
   Griffkanten. Ein Projekt, das nur die Formregeln benutzt, soll kein Druckprofil pflegen
   müssen. Preis: wer beides hat, schreibt die Pose zweimal.
6. **Die Bettebene hängt am Körper, nicht an der Kante.** Wird `bettkanten` je Kante mit
   nur einem Punkt aufgerufen, ist dieser Punkt sein eigenes Extrem — jede Kante läge am
   Bett. Der Bezug sind die Stützpunkte des ganzen Körpers, die Maske entsteht einmal.
7. **`sorte` braucht eine Bezugsachse, und die ist eine Annahme.** Ohne sie lassen sich Pad
   und Umriss nicht trennen (beide sind eine Stufe zwischen zwei parallelen Wänden). Die
   dünnste Hüllrichtung ist für plattenartige Teile richtig und steht als Annahme im
   Budget; für einen klotzigen Körper ist sie beliebig, und dann ist `sorte` es auch.
8. **Die Zählung von `unverrundet` hängt nicht an der Schwelle.** Naheliegend wäre, mit
   `griffkanten: nein` weniger zu melden. Aber die Regel findet *unverrundete* Kanten, nicht
   *zu klein verrundete* — ein Kantenbruch R1,0 macht aus 90° zwei 135°-Kanten, die ohnehin
   herausfallen. Die Schwelle sagt also, **was verlangt ist**, nicht **was gezählt wird**.
   Wer beides koppelte, bekäme eine Zahl, die je nach Pflegedatei etwas anderes bedeutet.

## Was ausdrücklich nicht gemacht wurde

- **Keine `teile.yaml` für die R6d-Teile.** Die Druckposen der 15 Teile sind nirgends
  dokumentiert; sie zu erfinden hieße, die Obergrenze durch eine Behauptung zu ersetzen.
  Das ist der eine offene Punkt, an dem die „unverrundet"-Zahlen hängen.
- **Kein STEP-Export**, kein Onshape-Aufruf, keine Renders. T41L/R und die anderen 13 Teile
  kommen aus `r6d-prints.step` von gestern; C00, H13S, H14S, R39, R77 bleiben ohne BRep.
- **Keine Toleranz gelockert.** Die einzige Zahl, die größer geworden ist, ist der
  Ankerradius von `kerbe` — und der ist kein Maß am Teil, sondern die Reichweite der Suche
  nach einem Nachbarn.
- **Keine Änderung an `absatz`, `unverrundet` oder `splitter` in dem, *was* sie finden**,
  außer den beschriebenen Ausnahmen. Die Absatz- und Kerbenzahlen je Teil sind unverändert;
  nur `splitter` zählt weniger, und zwar genau die 145 Fillet-Übergänge.
- **Kein Mesh-Weg für die Formregeln.** Unverändert `unentschieden` bei „kein BRep".
- **Keine neuen Bilder** in `docs/bilder/`.

## Wo Fable hinsehen sollte

- `rocking-photo-tray-r7/var/review/pruefstand.json`, Test
  `test_die_unerklaerten_kerben_sind_unveraendert[T41L]`: die sechs verbliebenen Zonen mit
  `anker_mm` je Zone — dort sieht man, welche Stelle mit welchem Radius gesucht hat.
- Ebenda `test_unverrundet_ist_ohne_teile_yaml_eine_obergrenze[…]` und im Terminal die
  `≤`-Zeilen.
- `rocking-photo-tray-r7/spec/test_tray_r2.py::test_die_randrundungen_bleiben_als_uebergaenge_sichtbar`
  — der Test, der den entfallenen `xfail` ersetzt.
- Offen für Marc: die Druckposen der R6d-Rahmenteile (dann werden aus den Obergrenzen
  Messwerte) und die Frage, ob an T41 die 0,341-mm-Nut bleibt.
