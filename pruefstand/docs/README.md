# Prüfstand — Dokumentation

Der Prüfstand misst fertige CAD-Geometrie gegen den Zustand der Maschine, in die sie
eingebaut wird. Er läuft als pytest-Plugin auf STEP- und STL-Dateien, ohne Onshape.
Alle Längen in mm, alle Volumen in mm³.

Diese Doku ist die mittlere Schicht zwischen `../README.md` (Kurzeinstieg, Befehle)
und `../SPEC.md` (verbindlicher Schnittstellenvertrag).

## Wegweiser

| Datei | Wofür |
|---|---|
| [warum.md](warum.md) | Wozu das Werkzeug da ist. Der Fall, der einen Druck und einen Tag gekostet hat. |
| [konzepte.md](konzepte.md) | Wie man damit denkt: Maschinenkontext, Frame, Region, Hub, Schnittstellen, Form, Fehler gegen Warnung, Prüfbudget. |
| [primitive.md](primitive.md) | Die beschriebenen Primitive: Zweck, Signatur, Rückgabe, Bild, echtes Beispiel. |
| [erste-pruefung.md](erste-pruefung.md) | Schritt für Schritt von `pruefstand.yaml` bis zum ersten roten Test. |
| [fallstricke.md](fallstricke.md) | Was schon Zeit gekostet hat. |
| [Purpose coverage](purpose-coverage.md) | Require a disposition for every expected occurrence, source contribution and finding; keep unreviewed or unresolved items visible. |
| [Purpose dependencies](purpose-dependencies.md) | Generate functional dependencies with FeatureScript, bind native witnesses to assembly occurrences, and check orphaned features offline. |

## Was heute fertig ist

`gap`, `overlap`, `coverage`, `protrusion`, `same_as` und `interface_ok` sind gebaut und
werden von `pruefstand` exportiert, dazu `sweep`, `access`, `screw_chain`, `print_pose`,
`stability`, `relevance` und die vier Formregeln `absatz`, `kerbe`, `unverrundet`,
`splitter`. Die Trägerschicht: `Machine`, `State`, `Scene`, `Frame`,
`Region`, `Body`, `Parts`, `Interface`, `load_step`, `load_mesh` und das pytest-Plugin.

Neu in Etappe 5 (18.09.2026) — sechs Werkzeuglücken aus der R7-Bestandsaufnahme:

- `gap.penetrating` wird **nachgerechnet** statt aus „Abstand 0" geschlossen: exakter
  Schnitt, wo beide Körper ein BRep haben, sonst Eindringtiefe über 0,01 mm. Formschluss
  ist damit kein Befund mehr; woher die Aussage kommt, steht in `penetration_auf`.
- `kerbe`: Ankerradius `max(anker_mm, anker_faktor · Spalt)` statt fester 2,5 mm — die
  13 Rahmenfugen der R6d-Platten sind erklärt, die echten Nuten nicht. Je Teil in
  `form.yaml` überschreibbar.
- `unverrundet` kennzeichnet sich ohne Druckpose und Kontext selbst als **Obergrenze**
  (`obergrenze`, im Terminal `≤`); mit `spec/teile.yaml` (`pruefstand.teile/1`:
  Druckpose, Auflage, `griffkanten: ja/nein`, Schwelle je Teil) fallen Bett- und
  Fugenkanten heraus.
- `splitter` meldet tangentiale Übergänge auf eine Rundung nicht mehr als
  „unverschmolzen" — sie stehen in `rundungsuebergaenge`. Über die 15 R6d-Teile waren
  das alle 145 Treffer.
- `absatz` sortiert selbst: `sorte` ∈ `umriss` / `banddicke` / `pad`, dazu `sorten`
  und die verwendete `achse`.
- `Frame.direction_to_local` als Gegenstück zu `direction_to_world`.

Neu in Etappe 4 (18.09.2026):

- `kanten(body)` klassifiziert jede Kante nach Länge, Typ, Knickwinkel und **konvex /
  konkav / tangential** — die Grundlage der vier Stilregeln `absatz`, `kerbe`,
  `unverrundet`, `splitter`. Alle vier sind Warnungen und rechnen nur auf dem BRep;
  siehe [konzepte.md](konzepte.md#7-form-die-stilregeln-messen).
- Pflegedatei `spec/form.yaml` (`pruefstand.form/1`) für enge Stellen, die gewollt sind.
- **Prüfbudget** an jedem Testeintrag und als Summe im Kopf des Berichts: was gemessen,
  was übersprungen und was angenommen wurde.
- `status: not_built_yet` in `schrauben.yaml`, `schnittstellen.yaml` und `montage.yaml`:
  beschrieben, aber noch nicht gebaut — die Prüfung wird unentschieden, nicht grün.

Neu in Etappe 3 (17.09.2026):

- `Region.crop` meldet über `rand_schneidet_material`, ob das Messfenster Material
  angeschnitten hat; jedes Primitiv reicht das als `fenster_schneidet_material` durch
  (Terminal: `~` vor der Zeile). Siehe
  [konzepte.md](konzepte.md#5-fenster-die-sich-selbst-messen).
- `Interface` / `interface_ok` mit `spec/schnittstellen.yaml`: Schnittstellen benennen
  statt Fenster platzieren, mit den Ausgängen `UNIQUE` / `AMBIGUOUS` / `MISSING`.
- `same_as(..., erwartet=[Region, …])` für Unterschiede, die keine Abweichung sind.
- `urteil_auf` an jedem Messwert (`[brep]` / `[mesh]` im Terminal), Kontaktorte bei
  `overlap` und die gemessene Pose je Test im JSON-Bericht.

Drei echte Projekte laufen damit durch (selbst ausgeführt):

```
rocking-photo-tray-r6d-belt-clamp-r1    13 passed,  2 xfailed,             4 warnings in  4.40s
rocking-photo-tray-r6d-hopper-floor-r1  27 passed,  2 xfailed,  3 warnung, 4 warnings in  9.63s
rocking-photo-tray-r6d-tray-r1          73 passed,  1 xfailed,  1 warnung, 4 warnings in 38.86s
rocking-photo-tray-r7 (spec/)          220 passed,  7 xfailed, 50 warnung, 4 warnings in 106.94s
```

Die `warnung`-Zeilen sind neu und gewollt: die Formregeln melden an der Wanne 16 scharfe
Außenkanten, am Hopperboden sechs Absätze, 32 scharfe Kanten und 50 Splitter. Marc
entscheidet, was davon Absicht ist; der Exit-Code bleibt 0.

Die `xfailed` sind gewollt: sie halten bekannte Fehler fest, damit niemand sie
versehentlich wieder einbaut.

## Was noch nicht fertig ist

`sweep`, `access`, `screw_chain`, `print_pose`, `stability` und `relevance` laufen und
sind exportiert, aber in [primitive.md](primitive.md#in-arbeit) noch nicht mit Signatur,
Rückgabetabelle und echtem Beispiel beschrieben. Bis dahin sind die Docstrings in
`src/pruefstand/primitives/` die Quelle — hier steht keine Signatur, die nicht an einem
echten Lauf geprüft wurde.

Ausdrücklich **nicht** gebaut (Beschluss zu Etappe 3, `PLAN-etappe3.md` Abschnitt 5):
ein fünfter Ausgang `UNSUPPORTED`, die sechsteilige Toleranz-Taxonomie, das
Face-ID-Sidecar und die konservative Rotationsschranke. Sie kommen, sobald ein zweiter
Fall wie die 0,321 mm des Hopperbodens auftaucht.

## Bilder

Alle Abbildungen liegen unter [`bilder/`](bilder/), die erzeugenden Skripte unter
[`bilder/src/`](bilder/src/). Die schematischen Skizzen stammen aus `schemata.py`,
die Bilder aus echter Geometrie aus `real_bilder.py` und `warum_13mm.py`. Jede Zahl in
den „real"-Bildern kommt aus einem echten Aufruf des jeweiligen Primitivs.

| Bild | Zeigt |
|---|---|
| `warum-13mm.png` | Riemenklemme R6d gegen R1, echter Schnitt in der Riemenebene |
| `schema-kontext.png` | Frame, Motion `hub`, Region — schematisch |
| `schema-gap/overlap/coverage/protrusion/same_as.png` | je ein Primitiv, schematisch |
| `real-gap.png` | Hopperboden zur Hubplatte, `min_mm=0.99999` |
| `real-overlap.png` | Zahnspitzen im Riemenband, `volume_mm3=14.07504` |
| `real-coverage.png` | 220 Abtastpunkte der Bodenecken, R1 gegen R6d |
| `real-same_as.png` | Messfenster hinter lokal Y −33, `max_deviation_mm=0.00052` |

```bash
cd /Users/mneuhaus/Workspace/cad/toolroom/pruefstand/docs/bilder/src
uv run --project ../../.. --with matplotlib python schemata.py
uv run --project ../../.. --with matplotlib python warum_13mm.py
uv run --project ../../.. --with matplotlib python real_bilder.py
```
