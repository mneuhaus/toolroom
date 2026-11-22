# Prüfstand — Spezifikation Ausbaustufe 1 (Punkt 1 + 2 des HANDOFF)

Stand 17.09.2026. Entwurf: Fable. Implementierung: Opus-Subagent. Abnahme: Fable.
Hintergrund und Entscheidungen: `HANDOFF.md` im selben Ordner. Diese Datei ist die
verbindliche Schnittstelle; die Referenztests in
`step-feeder/rocking-photo-tray-r6d-hopper-floor-r1/spec/` und
`step-feeder/rocking-photo-tray-r6d-belt-clamp-r1/spec/` sind gegen genau diese
Schnittstelle geschrieben und dürfen **nicht** an die Implementierung angepasst werden.
Wenn ein Test nicht grün wird, gilt: Messwert melden, Toleranz nicht selbst lockern.

## Umgebung

- Eigenes uv-Projekt `toolroom/pruefstand/` (Python 3.13, `pyproject.toml` liegt vor).
  Verifiziert lauffähig: build123d 0.10.0 **mit ocp-gordon==0.2.0** (0.3.1 bricht `OCP.collections`),
  python-fcl 0.7, trimesh, pytest, cad-khana als editable Path-Dependency.
- Ausführen: `cd toolroom/pruefstand && uv run pytest <projekt>/spec -q`.
- Kein Onshape-Aufruf, nirgends. Alles läuft auf Dateien.
- Große Ausgaben (JSON, PNG) nach `var/review/` des jeweiligen Projekts, im Terminal nur Kopfzeilen.

## Paket `src/pruefstand/`

```
__init__.py        exportiert: Machine, State, Scene, Body, Parts, Frame, Region,
                   load_step, load_mesh, gap, overlap, coverage, protrusion, same_as
frame.py           Frame
region.py          Region
interface.py       Interface, Match, InterfaceResult, interface_ok, load_interfaces
form.py            Kante, kanten, absatz, kerbe, unverrundet, splitter, FormSpec, load_form,
                   plattenachse, SORTEN
teile.py           Teil, Auflage, TeileSpec, load_teile, find_teile (spec/teile.yaml)
body.py            Body, Parts, load_step, load_mesh
machine.py         Machine, State, Scene (+ Machine.from_manifest)
primitives/        gap.py overlap.py coverage.py protrusion.py same_as.py  (+ _fcl.py Kollisionskern)
results.py         GapResult, OverlapResult, CoverageResult, ProtrusionResult, SameAsResult
                   (+ record(), Prüfbudget, ohne_urteil(), pruefe_bau_status())
pytest_plugin.py   Fixtures project/machine, Marker warnung, Bericht var/review/pruefstand.json
cli.py             `pruefstand run <projekt>` (pytest-Wrapper), `pruefstand machine <build_machine.py>` optional
```

Alle Längen in **mm**, Volumen in mm³. Koordinaten als `numpy`-Arrays oder Sequenzen.

### Frame

```python
Frame(rotation: 3x3, translation: 3)      # world = R @ local + t
Frame.identity()
Frame.rot_x(deg, translation) / rot_y / rot_z
frame.to_world(pts) / frame.to_local(pts)  # (N,3) oder (3,)
frame.direction_to_world(vec) / frame.direction_to_local(vec)
                                      # nur drehen, nicht verschieben -- für Normalen,
                                      # Achsen, Halbierende. `to_local` zöge die
                                      # Verschiebung ab und machte aus einer Richtung
                                      # einen Ort.
frame.matrix() -> 4x4
```

Für R6d gilt exakt (aus den vorhandenen `check_geometry.py`):
`R = [[1,0,0],[0,c,s],[0,-s,c]]`, `c,s = cos 25°, sin 25°`, `t = (0,0,203)`,
`local = R.T @ (world − t)`. Der Hub verschiebt bewegte Körper um `R @ (0,0,hub)` in Welt.

### Region

```python
Region.box(frame, lo, hi)             # achsparalleler Quader im Frame (Volumen ODER Kriterium)
Region.cylinder(frame, origin, axis, radius, length, inner_radius=0.0)
                                      # runder Ausschnitt um eine Achse; inner_radius > 0 -> Ring
Region.points(frame, pts)             # explizite Abtastpunkte (für coverage)
Region.plane_grid(frame, plane='xy', u=(u0,u1,step), v=(v0,v1,step), w=0.0)  # Gitter in Frame-Ebene
region.solid() -> build123d Solid     # nur box (in Welt)
region.contains(pts_world) -> bool[N] # box
region.sample_points() -> (N,3) Welt  # points / plane_grid
region.meta['rand_schneidet_material']    # nach crop(): hat das Fenster Material angeschnitten?
                                      # box: irgendein benutzter Punkt liegt auf einer der sechs
                                      #   Wände (Toleranz 1e-6 mm; Clipping legt Punkte exakt dorthin).
                                      # cylinder: ein Dreieck liegt beidseits der MANTELwand
                                      #   (bzw. der Innenwand beim Ring), gemessen VOR der
                                      #   Unterteilung. Die Deckel zählen nicht mit -- sie stehen
                                      #   als meta['rand_deckel_schneidet_material'].
                                      # ODER-Sammlung über alle crop()-Aufrufe derselben Region:
                                      # ein Primitiv schneidet beide Seiten zu, und eine reicht.
                                      # Schlüssel fehlt = es wurde nie zugeschnitten.
region.crop(mesh) -> trimesh          # an den sechs Halbräumen der Box abgeschnitten (box);
                                      # Dreiecke werden zerschnitten, Ergebnis ist nicht wasserdicht.
                                      # Nicht „nur ganz enthaltene Dreiecke": Maschinendreiecke sind bis
                                      # 25 mm groß, dabei bliebe in jedem sinnvollen Messfenster nichts übrig.
```

### Body / Parts

```python
Body(key, name, solid: Solid|None, mesh: trimesh.Trimesh|None, moving: bool=False, source: Path)
body.mesh          # lazy: aus solid tesselliert (tolerance 0.01, angular 0.1) und gecacht in var/review/<key>.stl, wenn ein Projekt bekannt ist
body.solid         # None, wenn Quelle STL
body.volume_mm3, body.bounds(frame=None) -> (lo, hi), body.vertices(frame=None) -> (N,3)
body.moved(frame, delta) -> Body      # Kopie um delta (im Frame) verschoben; für absichtliche Rückbau-Tests
body.transformed(matrix4x4) -> Body

load_step(path, moving=False) -> Parts     # eine Body je Solid; key = STEP-Produktname (build123d: compound.children[i].label; bei genau einem Solid ohne children der compound.label)
load_mesh(path, key, moving=False) -> Body
parts.one(key=None, moving=None) -> Body   # genau ein Solid, sonst Fehler; key/moving überschreiben
parts.find(substring) -> Body              # genau ein Treffer (case-insensitiv), sonst Fehler mit Liste
parts.find_all(substring) -> list[Body]
parts.all() -> list[Body]; parts[key]
```

### Machine / State / Scene

`machine.json` (Schema `pruefstand.machine/1`):

```json
{
  "schema": "pruefstand.machine/1",
  "name": "rocking-photo-tray-r6d", "revision": "R6d", "units": "mm",
  "frames": {"local": {"rotation": [[1,0,0],[0,c,s],[0,-s,c]], "translation": [0,0,203]}},
  "motions": {"hub": {"kind": "translation", "frame": "local", "axis": [0,0,1], "range": [0,130], "default": 0}},
  "bodies": [
    {"key": "T05", "name": "T05 R6d 249.2mm hopper floor", "role": "print", "moving": false,
     "file": "../local/T05.stl", "format": "stl", "sha256": "…", "boundsMm": [[…],[…]], "volumeMm3": 111021.9}
  ],
  "source": {"kind": "manifest", "path": "../local/manifest.json", "built": "2026-09-17T…", "note": "…"}
}
```

Pfade relativ zur `machine.json`. `format` ∈ `stl | step`; bei `step` mit mehreren Solids zusätzlich
`"solid": <index oder Produktname>`. Bewegte Körper folgen **allen** Motions (Stufe 1: genau eine, `hub`).

```python
Machine.load(path) -> Machine
Machine.from_manifest(manifest_json, out_dir, frames, motions, name, revision) -> Machine   # schreibt out_dir/machine.json
machine.frame('local') -> Frame
machine.body('T05') -> Body                 # Ruhelage, moving-Flag aus machine.json
machine.state(hub=65) -> State              # Motion-Werte; fehlende = default; außerhalb range = ValueError
machine.scene(hub=65) -> Scene              # = machine.scene_at(machine.state(hub=65))
scene.bodies -> list[Body] (bereits verschoben), scene.fixed, scene.moving
scene.without(*keys) -> Scene; scene.only(*keys) -> Scene
scene.displace(body) -> Body                # wendet die Motion des Scene-States auf einen Fremdkörper mit moving=True an
```

Primitive nehmen als `b` einen `Body`, eine Liste von Bodies oder eine `Scene`. Optional `at=State|Scene`:
dann wird jeder übergebene Body mit `moving=True` um die Motion verschoben (Scene-Bodies sind es schon).

### Primitive und Ergebnisse

Alle Ergebnisse: `bool(result)` = bestanden nach dem Kriterium des Aufrufs (falls angegeben), `repr()`
enthält die Messwerte, `.as_dict()` für den Bericht. Jedes Ergebnis wird automatisch mit
`results.record(test_id, name, dict)` in den laufenden Testbericht geschrieben.

**„Nichts gemessen" ist nicht bestanden.** Wenn eine Region nach dem Zuschneiden keine Geometrie
mehr enthält, setzt das Primitiv `result.nichts_gemessen = True` und `result.leer_grund`, und das
pytest-Plugin macht den Test rot — auch wenn die Assertion formal durchginge (`gap` liefert dann
`min_mm = inf`, `same_as` `samples = 0`, `coverage` `total = 0`). Ohne diese Regel meldet eine
falsch gesetzte Messbox stillschweigend „grün", und das ist der gefährlichste Zustand, den ein
Prüfwerkzeug haben kann. Jedes neue Primitiv muss die Konvention mittragen.

**Ein Fenster, das Material schneidet, sagt das.** Die Umkehrung des leeren Fensters ist das
zu volle: liegt die Fensterwand im Material, misst die Messung am Rand sich selbst. Der Zylinder
r 4,5 über dem Bund Ø10,5 liefert 4,41 statt 3,95 — den Fensterradius. Jedes Primitiv, das eine
Region zuschneidet, setzt deshalb `result.fenster_schneidet_material` und schreibt es in
`as_dict()`; im Terminalbericht trägt die Zeile ein `~`.

```python
result.fenster_schneidet_material   # True  -- mindestens eine Fensterwand liegt im Material
                                    # False -- zugeschnitten, keine Wand berührt Material
                                    # None  -- nichts zugeschnitten, also keine Aussage
                                    #          (kein within/region, oder exakter Weg von overlap)
```

Das ist **kein Urteil**: `passed` bleibt davon unberührt. Ein `within=` über einen großen
Maschinenkörper schneidet immer an. Der Hinweis sagt nur, dass ein Messwert am Fensterrand
erklärungsbedürftig ist — und er darf nicht bei jeder sauberen Messung angehen, sonst ist er
keiner (deshalb der Kreuzungstest statt `rand_unschaerfe_mm`, siehe Region oben).

**Vier Ausgänge, nicht zwei.** Ein Messwert und ein Urteil sind zweierlei, und zwei der vier
Ausgänge sind gar kein Urteil:

| Ausgang | Bedeutung | Feld | Lauf |
|---|---|---|---|
| bestanden / verletzt | gemessen, Kriterium erfüllt bzw. nicht | `passed` | grün / rot |
| nichts gemessen | die Region enthielt keine Geometrie | `nichts_gemessen`, `leer_grund` | rot |
| unentschieden | die Anforderung ist keiner Geometrie zugeordnet | `unentschieden`, `offen_grund` | eigener Ausgang `U`, Rückgabewert ≠ 0 |
| technischer Fehler | das Messverfahren ist gescheitert | `technischer_fehler`, `fehler_grund` | rot |

**Eine Obergrenze ist kein Messwert.** Fehlt einer Messung eine Angabe, mit der Treffer
herausgefallen wären, setzt sie `result.obergrenze = True` und nennt in `_obergrenze_felder` die
betroffenen Zahlen. Im JSON steht `obergrenze` samt Feldliste, im Terminalbericht ein `≤` vor
genau diesen Werten (`unverrundet(anzahl=≤104, gesamt_mm=≤2461.4, radius_mm=4.2)`). Kein
Urteil — aber der Unterschied zwischen „104 scharfe Kanten" und „höchstens 104" ist der
zwischen einem Befund und einer Hausnummer.

„Unentschieden" ist bewusst kein Fehlschlag: ein nicht gefundener Anker beweist keinen Verstoß,
er beweist gar nichts. Er darf aber auch nicht grün enden, sonst gehen unverbundene Anforderungen
still durch. Reihenfolge, wenn mehreres zutrifft: technischer Fehler > unentschieden > nichts
gemessen. Alle drei setzen `passed = False`.

**Woher das Urteil kommt, steht am Messwert.** `result.urteil_auf` ist `'brep'` oder `'mesh'` und
sagt, worauf `passed` tatsächlich beruht. Ein exakt gerechneter Nebenwert macht ein abgetastetes
Urteil nicht exakt: `same_as` liefert `diff_mm3` aus dem BRep (`exact=True`), urteilt aber über die
abgetastete Mesh-Abweichung — `urteil_auf='mesh'`. Im Terminalbericht steht es als `[brep]` bzw.
`[mesh]` direkt hinter dem Messwert. Jedes Primitiv setzt es, ohne Ausnahme:

| Primitiv | `urteil_auf` | warum |
|---|---|---|
| `gap` | `'mesh'` | der Kollisionskern rechnet auf BVH-Modellen, auch wenn beide Körper aus STEP kommen |
| `overlap` | `'brep'`, sonst `'mesh'` | exakt nur, wenn **alle** beteiligten Körper einen Solid haben |
| `coverage` | `'mesh'` | Strahlen gegen Körpernetze |
| `protrusion` | `'brep'`, sonst `'mesh'` | mit Solid boolescher Schnitt, ohne gezählte Eckpunkte |
| `same_as` | `'mesh'` | Urteil aus der Abtastung, `diff_mm3` nur Nebenwert |
| `sweep` | `'mesh'` | „Bewegung frei" gilt für die Tessellation, nicht für die exakten Flächen |
| `access` | `'mesh'` | Werkzeughülle gegen Körpernetze |
| `interface_ok` | `'brep'` | Radius, Achswinkel, Versatz kommen aus den exakten Flächen; der Partnerspalt daneben ist ein eigener `gap`-Eintrag und damit `'mesh'` |

**Ein gescheiterter Boolean ist kein Volumen von null.** Die Primitive rechnen einen Kernfehler nie
in eine Zahl um, sondern erheben `results.KernelFehler`. Ein hart abgestürzter Kern (Signal) nimmt
sonst den ganzen Lauf mit; dagegen steht `pruefstand.kernel`, siehe unten.

```python
gap(a, b, at=None, within: Region|None=None, ignore: Region|None=None) -> GapResult
    # min_mm, point_a, point_b (Welt), pair (key_a, key_b), per_body {key: min_mm}
    # Mesh-basiert (fcl DistanceRequest auf BVH-Modellen). within/ignore beschneiden beide Meshes
    # vorher (Region.crop bzw. Komplement). Bei Liste/Scene: min über alle, per_body gefüllt.
    # Berührung und Durchdringung liefern beide min_mm = 0.0 -- `penetrating` wird deshalb
    # NACHGERECHNET, nie aus `distance() == 0` geschlossen:
    #   - beide Körper mit Solid und ohne within/ignore -> exakter Schnitt > 0 mm³
    #     (penetration_auf='brep'),
    #   - sonst Netz: größte Tiefe, mit der Stützpunkte UND Facettenmitten des einen im
    #     anderen liegen (trimesh signed_distance), Schwelle DURCHDRINGUNG_MM = 0,01 mm
    #     (penetration_auf='mesh', durchdringung_mm = der Wert),
    #   - offenes Netz -> penetration_auf='unentschieden', penetrating bleibt False und
    #     das Übersprungene steht im Budget.
    # NICHT über fcl.penetration_depth: für koinzidente Flächen liefert der Kern dort die
    # volle Körpertiefe (zwei bündige 10er-Würfel -> 10,0 mm). Genau daran sah der
    # Formschluss T40↔T41 wie eine Kollision aus.
    # `urteil_auf` bleibt 'mesh' -- der Abstand kommt aus dem Netz, auch wenn `penetrating`
    # exakt ist.

overlap(a, b, at=None, within: Region|None=None) -> OverlapResult
    # exact: bool. Wenn beide Seiten Solids haben: build123d intersect, volume_mm3 (Summe über Solids),
    #   within = zusätzlich mit region.solid() geschnitten.
    # Sonst Mesh-Kern: fcl CollisionRequest(enable_contact) -> collides: bool, contacts: int,
    #   max_penetration_mm; volume_mm3 = None. within: Meshes croppen.
    # Bei Liste/Scene: pairs = [(key_a, key_b, volume_mm3|None, collides)], .collides = any,
    #   .volume_mm3 = Summe der exakten. Bounding-Box-Vorfilter (0.5 mm Puffer) vor jedem Paar.

coverage(by, region, direction, at=None) -> CoverageResult
    # Strahl je Abtastpunkt der Region entlang `direction` (Welt). Start = Punkt − direction·(Diagonale
    # der Gesamt-BBox aller `by` + 50 mm), also garantiert außerhalb aller beteiligten Körper.
    # covered = Strahl trifft irgendeinen Body aus `by` (andere Körper sind transparent).
    # total, covered, open (Anzahl), open_points (Welt), fraction; .map_png: PNG der Punkte
    # (grün/rot) in der Region-Ebene nach var/review/coverage-<test>.png, falls Projekt bekannt.

protrusion(part, volume: Region, at=None) -> ProtrusionResult
    # exakt: part.solid ∩ volume.solid(); volume_mm3; Mesh-Fallback: Anzahl Vertices in Region (hits)

same_as(part, predecessor, region: Region, at=None, max_deviation_mm=None,
        erwartet: list[Region] = ()) -> SameAsResult
    # predecessor fehlt (None/leer) -> unentschieden, NICHT „unverändert".
    # Beide auf Region beschneiden. Exakt (beide Solids): symmetrische Differenz -> diff_mm3.
    # Immer: max_deviation_mm = max über beide Richtungen von (Oberflächenpunkte des einen -> nächster
    # Punkt auf dem anderen), Abtastung ≥ 5 Punkte/mm² aber gedeckelt bei 200k Punkten, trimesh proximity.
    # erwartet: Regionen, in denen ein Unterschied keine Abweichung ist (ergänzte Pilotbohrung,
    #   entfallener Steg). Abtastpunkte darin werden auf BEIDEN Seiten verworfen, ihre Zahl steht
    #   in result.erwartet_ausgenommen. diff_mm3 zählt sie WEITER MIT -- nur das Urteil nimmt sie
    #   heraus, damit im Bericht sichtbar bleibt, wie groß der erwartete Unterschied war.

interface_ok(iface: Interface, parts, at=None, machine=None, partner_body=None) -> InterfaceResult
    # Schnittstelle (siehe unten) gegen die Geometrie prüfen. urteil_auf='brep'.
    # parts: Parts, Liste von Bodies oder ein Body; iface.body wird darin wie Parts.find gesucht.
    #   Kein eindeutiger Treffer -> unentschieden (offen_grund), kein Urteil.
    # Ablauf: iface.match(body) -> status. Nur bei UNIQUE wird gemessen und geurteilt.
    #   AMBIGUOUS/MISSING -> unentschieden. Niemals der „beste" Kandidat.
    # Geurteilt wird gegen iface.tolerance: |radius_mm - radius| <= tol.radius,
    #   axis_deg <= tol.axis_deg, |offset_mm - pitch_radius| <= tol.offset.
    #   Jede Verletzung landet im Klartext samt Messwert in result.verletzt.
    # partner gesetzt: zusätzlich gap(body, partner, within=iface.region()) -> gap_mm;
    #   Formschluss = 0.0 ± tol.gap (Vorgabe 0.02). Partner nicht auflösbar -> unentschieden;
    #   Partner nicht im Fenster -> nichts gemessen. Beides macht rot, keins macht grün.
```

### Interface

Pflegedatei `spec/schnittstellen.yaml`, Schema `pruefstand.schnittstellen/1`. Wurzel ist eine
Abbildung mit `schema` und der Liste `schnittstellen` (wie `schrauben.yaml`, nicht die blanke
Liste aus dem Entwurf). Jeder Formfehler fliegt beim Laden, nicht beim Messen.

```yaml
schema: pruefstand.schnittstellen/1
schnittstellen:
  - id: journal_pin        # eindeutig in der Datei
    kind: pin              # pin | bore | seat | plane
    body: T60              # Suchbegriff wie bei Parts.find
    frame: world           # Name aus machine.json, oder world (Vorgabe)
    axis: [1, 0, 0]        # Achse (pin/bore/seat) bzw. Flächennormale (plane), wird normiert
    origin: [-104.3, 135, 236]
    radius: 3.95           # Pflicht außer bei plane
    inner_radius: 9.5      # optional: macht das Fenster zum Ring
    pitch_radius: 9.5      # optional: Teilkreis, wenn die Flächen NEBEN der Achse liegen
    length: 7.4            # Fensterlänge ab origin entlang axis
    size: [20, 10]         # nur plane: Kantenlängen des Fensters quer zur Normale (Pflicht)
    count: 4               # optional: so viele Flächen müssen es sein (Vorgabe 1)
    partner: H608          # optional: Maschinenkörper für den Formschlussabstand
    tolerance: {radius: 0.05, axis_deg: 0.1, offset: 0.05, gap: 0.02}   # Vorgaben
```

```python
load_interfaces(path) -> list[Interface]      # wirft bei Schema-, Pflicht-, Nullvektor-,
                                              # kind-, radius/size-, count-, tolerance- und
                                              # Doppel-id-Fehlern
interfaces_by_id(ifaces) -> dict[str, Interface]

iface.region(machine=None, zuschlag_mm=0.5) -> Region
    # pin/bore/seat -> Region.cylinder(origin, axis, radius + pitch_radius + zuschlag,
    #                                  length, inner_radius); plane -> Region.box um die Fläche
    #                                  herum (±length/2 entlang der Normale).
    # Der Zuschlag ist Absicht: ein Fenster exakt auf der Oberfläche ist eine Gussform, kein
    # Fenster -- es berührt die Fläche überall und der Randhinweis ginge immer an.

iface.match(body, machine=None) -> Match
    # Sucht im BRep: Zylinderflächen nach Radius, Achsrichtung (Vorzeichen egal) und Abstand
    # der Flächenachse zur Schnittstellenachse; Ebenen nach Normale und Abstand entlang dieser.
    # Gesucht wird mit SUCHFENSTER = max(tolerance, {radius 0.25 mm, axis_deg 1.0°, offset
    # 0.25 mm}) -- WEITER als geurteilt wird. Sonst könnte eine gefundene Fläche nie durchfallen
    # (sie wäre mit genau der Urteilstoleranz gefunden worden), und ein knapp verfehltes Maß
    # verschwände als MISSING statt als Fehler aufzufallen.
    # body ohne Solid (aus STL) -> MISSING mit Begründung, nie ein Netz-Ratespiel.

Match(interface_id, status, candidates, erwartet, grund)
    status == 'UNIQUE'     genau `count` Flächen erfüllen alle Kriterien
           == 'AMBIGUOUS'  mehr als `count`
           == 'MISSING'    weniger als `count`
    candidates: [{'face': '<body.key>#<index>', 'radius_mm', 'axis_deg', 'offset_mm',
                  'axial_mm' | 'quer_mm', 'area_mm2'}, …]   -- ALLE, nicht nur der beste
    match.best() liefert den ersten Kandidaten und ist nur bei UNIQUE zu benutzen.
```

`face` ist ein Index in `body.solid.faces()`, kein stabiler Face-Identifier. Er dient dem
Nachsehen im selben Lauf; ein Sidecar mit dauerhaften IDs ist ausdrücklich nicht Teil dieser
Ausbaustufe.

### Form (`form.py`) — Absätze, Kerben, Rundungen, Splitter

Vier Stilregeln auf dem BRep, alle **Warnung** (`@pytest.mark.warnung`), alle `urteil_auf='brep'`.
Ein Körper ohne Solid wird `unentschieden` mit dem Grund „kein BRep" und meldet das im
Prüfbudget — ein Dreiecksnetz knickt an jeder Facette, Kanten sind daran nicht messbar.

```python
kanten(body) -> list[Kante]
    # TopExp.MapShapesAndAncestors_s(EDGE -> FACE). Je Kante:
    #   index, typ (Line/Circle/…), laenge_mm, mitte (Welt), richtung (Tangente in der Mitte),
    #   knick_deg (Winkel der beiden Flächennormalen in der Kantenmitte),
    #   art: 'konvex' | 'konkav' | 'tangential' (Knick < 1°) | 'unentschieden',
    #   normalen, flaechen ('<key>#i' wie bei interface_ok), flaechen_mm2,
    #   radius_mm + kreis_mitte (nur Circle), geschlossen, halbierende (Eigenschaft).
    # Konvexität: Richtung von der Kante IN die Nachbarfläche hinein (n2 x t, Vorzeichen
    #   per Probepunkt auf der Fläche); konvex, wenn sie unter die Außennormale der ersten
    #   Fläche führt. Der naheliegende Schwerpunkt-Test kippt an T05 an sechs Kanten
    #   (0,02–0,57 mm lang an einer 902 mm² großen Ebene) und ist deshalb nicht der Weg.
    # Mesh-only -> leere Liste (nicht: Ausnahme).

absatz(body, *, versatz_mm=(0.3, 3.0), parallel_deg=2.0, achse=None) -> AbsatzResult
    # Kantenpaar konvex + konkav an DERSELBEN Fläche (der Stufe), parallel < parallel_deg,
    # exakter Kantenabstand (BRepExtrema) in versatz_mm, Stufe schmaler als lang, und die
    # beiden Nachbarwände parallel < parallel_deg. Ergebnis: anzahl, max_versatz_mm,
    # sorten {umriss, banddicke, pad}, achse,
    # absaetze[{ort, versatz_mm, laenge_mm, sorte, flaechen[Wand,Stufe,Wand], stufe_mm2, kanten}].
    # `sorte` nach dem Verfahren aus rocking-photo-tray-r7/src/t41_details.py, bezogen auf
    # die Plattenachse (`achse`, Vorgabe: dünnste Hüllrichtung, `form.plattenachse`):
    #   umriss    beide Wände quer zur Achse, Stufe ebenfalls quer -> die Silhouette springt
    #   banddicke beide Wände quer, Stufe in einer Ebene der Achse -> die Stirnfläche des
    #             Randbandes wird stufig schmaler
    #   pad       eine Wand längs der Achse -> aufgesetzter Block auf der großen Fläche
    # Grenze |n·achse| < 0,3 (17°). An T41L/T41R liefert das 14 bzw. 11 Konturabsätze --
    # dieselben Zahlen wie die Handrechnung, die die Sorten bisher außerhalb ermittelte.
    # Referenz: zwei um 1,5 mm versetzt vereinigte Quader -> 2 (einer je Seite);
    #   bündig, 0,1 mm oder 5 mm -> 0. Wanne T01 -> 0. Hopperboden T05 -> 6.

kerbe(body, kontext=None, at=None, *, schrauben=(), erklaert=None, machine=None,
      spalt_mm=(0.2, 2.5), knick_deg=60.0, raster_mm=5.0,
      anker_mm=None, anker_faktor=None) -> KerbeResult
    # Konkave Kanten mit Knick > knick_deg; Strahl (BRepIntCurveSurface_Inter) von der
    # Kantenmitte entlang BEIDER Flächennormalen; trifft er den eigenen Körper in
    # spalt_mm, ist die Stelle eng. Bündelung im raster_mm-Raster zu Zonen.
    # Erklärt ist eine Zone, wenn in IHREM Ankerradius ein Kontextkörper (Scene, Liste von
    #   Szenen = alle Posen, oder Bodies) oder eine Schraube aus schrauben.yaml liegt, oder
    #   wenn sie in spec/form.yaml unter `erklaert:` steht.
    # Ankerradius je Zone = max(anker_mm, anker_faktor · spalt), Vorgaben 2,5 mm und 3,0.
    #   Ein fester Radius ist falsch: ein breiter Sitz nimmt ein Teil auf, das weiter weg
    #   beginnt. Gemessen an den R6d-Teilen erklärt Faktor 2 keine einzige der 13
    #   Rahmenfugen (2 · 1,45 = 2,90 mm gegen Partner in 3,7–4,0 mm), Faktor 3 genau diese
    #   13 und keine weitere Stelle -- der nächste Befund darüber liegt bei 5,53 mm.
    #   Beides je Aufruf und je Teil in form.yaml (`anker_mm:`, `anker_faktor:`)
    #   überschreibbar; Reihenfolge Aufruf > Pflegedatei > Hausregel.
    # zonen[{ort, spalt_mm, laenge_mm, kanten, partner, partner_mm, anker_mm, erklaert, grund}],
    #   anzahl, unerklaert, enge_kanten_mm, min_spalt_mm. passed = keine unerklärte Zone.
    # Ohne Kontext steht das als `uebersprungen` im Budget -- eine Zone ohne Partner
    #   ist dann nicht „unerklärt", sondern ungeprüft.

unverrundet(body, pose=None, *, teil=None, kontext=None, at=None, machine=None,
            knick_deg=(80.0, 100.0), min_mm=5.0, radius_mm=None, fuge_mm=1.0)
    # Konvexe Kanten im Knickfenster, länger als min_mm, die Außenkanten sind: ein Strahl
    # von der Kantenmitte entlang der Winkelhalbierenden (0,02 mm Vorlauf) trifft den
    # eigenen Körper nicht. Vier Ausnahmen:
    #   - Bohrungsmündung: Kreiskante, deren Krümmungsmittelpunkt NICHT im Material liegt.
    #     An der Wanne sind das 7 Kreise (r 1,70 x4, r 3,10, r 6,10 x2); ohne diese
    #     Unterscheidung stünden 23 statt 16 Kandidaten im Bericht, und in ein Ø3,4-Loch
    #     passt kein R4,2.
    #   - Bettseite: gibt `pose` (alles, was `printing.pose_matrix` nimmt, oder ein
    #     Teilspec) eine Druckpose her, fallen Kanten innerhalb 0,5 mm über z_min heraus.
    #   - Auflage aus teile.yaml (`teil=`): Richtung zum Bett oder Bereich; die Bettebene
    #     hängt an den Stützpunkten des ganzen Körpers, nicht an der einzelnen Kante.
    #   - Fugenkanten: liegt mit `kontext=` (Scene / Szenenliste / Bodies) ein Nachbar
    #     näher als fuge_mm (1,0 mm = Nahfeld), stößt dort ein anderes Teil an.
    # Schwelle: teil.schwelle_mm -- R4,2 an frei anfassbaren Außenkanten, bei
    #   `griffkanten: nein` der Kantenbruch R1,0, `radius_mm` schlägt beides. Die ZÄHLUNG
    #   ändert das nicht (scharf ist scharf); die Schwelle steht am Ergebnis.
    # OBERGRENZE: fehlt Bettseite oder Fugenprüfung, ist `result.obergrenze = True`, die
    #   betroffenen Felder stehen in `_obergrenze_felder` (anzahl, gesamt_mm) und der
    #   Terminalbericht schreibt `anzahl=≤104`. Alle R6d-Zahlen sind solche Obergrenzen.
    # kanten[{ort, laenge_mm, typ, knick_deg, richtung, nach_aussen, flaechen, kante}],
    #   anzahl, gesamt_mm, radius_mm, ausnahmen {bettseite, fugenkanten, griffkanten}.

splitter(body, *, kante_mm=0.42, flaeche_mm2=1.0, nachbar_mm2=100.0, knick_deg=0.5,
         erklaert=None, machine=None)
    # Drei Listen: kurze_kanten (< Bahnbreite), winzige_flaechen (< flaeche_mm2 mit einem
    # Nachbarn > nachbar_mm2), unverschmolzen (Knick < knick_deg zwischen ZWEI
    # VERSCHIEDENEN und UNGEKRÜMMTEN Flächen). Zwei Einschränkungen, beide belegt:
    #   - die Naht eines Zylinders hat beide Male dieselbe Fläche als Nachbarn und Knick 0
    #     (an der Wanne 14 Falschmeldungen, alle an Rundzapfen);
    #   - ein sauber tangentialer Fillet ist ein Übergang Ebene->Zylinder/Torus mit Knick 0.
    #     Das ist das Merkmal selbst, kein Rest. Über die 15 R6d-Teile waren ALLE 145
    #     früheren Treffer von dieser Art; sie stehen jetzt in `rundungsuebergaenge`
    #     (mit `flaechentypen`), zählen aber nicht mit. Übrig bleibt der echte Fall: zwei
    #     Ebenen mit Knick 0, die eine Kante trennt -- eine Boolesche Spur.
    # Befunde in `erklaert`-Regionen werden mit Name, Grund und deklariertem Frame
    # klassifiziert, aber nie aus den drei Rohlisten entfernt. `erklaert` und
    # `unerklaert` zaehlen beide Gruppen; passed = keine unerklaerten Befunde.
    # Klassifiziert wird nur der aufgezeichnete Repraesentativpunkt (Kantenmitte bzw.
    # Flaechenzentrum), nicht die vollstaendige Aufnahme des Befunds in den Bereich.
    # Eine fehlgeschlagene BRep- oder Frame-Analyse ist `technischer_fehler`, nie 0 Treffer.
    # Nur BRep. Auf dem Netz wäre die Frage sinnlos (über die Hälfte aller Dreiecke einer
    # Tessellierung sind Winzlinge, ganz ohne Modellierfehler).
```

Pflegedatei `spec/form.yaml`, Schema `pruefstand.form/1` — optional, nur für erklärte Zonen:

```yaml
schema: pruefstand.form/1
teile:
  - key: T05
    anker_mm: 2.5          # optional: Mindest-Ankerradius dieses Teils
    anker_faktor: 3.0      # optional: Anker = max(anker_mm, anker_faktor · Spaltbreite)
    erklaert:
      - name: Kabelschlitz
        bereich: {frame: local, von: [-5, -20, -10], bis: [5, 20, 10]}   # frame default world
        grund: Kabelführung, bleibt offen
```

`load_form(path) -> FormSpec`, `find_form()` sucht `form.yaml` im Spec-Verzeichnis des Projekts
(None, wenn es keine gibt). Unbekannte Schlüssel, doppelte Namen und ein falsches Schema fliegen
beim Laden.

Pflegedatei `spec/teile.yaml`, Schema `pruefstand.teile/1` — was ein Druckteil über sich selbst
weiß, soweit die Formregeln es brauchen:

```yaml
schema: pruefstand.teile/1
teile:
  - key: T41L
    pose: {rotate: [0, 90, 0]}          # Druckpose, wie printing.pose_matrix sie nimmt
    auflage: {normale: [0, 0, -1]}      # Richtung ZUM Bett -- oder
    # auflage: {region: {frame: local, von: [...], bis: [...]}}
    griffkanten: nein                   # ja | nein -- frei anfassbar oder Rahmenteil
    radius_mm: 1.0                      # optional: Schwelle statt der Hausregel
```

`load_teile(path) -> TeileSpec`, `find_teile()` sucht `teile.yaml` im Spec-Verzeichnis. Genau
eines von `normale` / `region` ist Pflicht, `griffkanten` kennt nur ja/nein, `radius_mm` muss
positiv sein; alles andere fliegt als `TeileSpecFehler` beim Laden. Die Datei ersetzt
`druck.yaml` nicht (dort stehen Profil und Lastabschnitte für `print_pose` / `stability`) —
sie beantwortet die Fragen, die `unverrundet` sonst raten müsste.

### Prüfbudget

Jeder Testeintrag in `var/review/pruefstand.json` trägt `budget` mit vier Schlüsseln:

```python
budget = {
  'geprueft':      [{'primitiv', 'koerper_n', 'koerper' (max. 12 Namen), 'urteil_auf', 'pose'}],
  'uebersprungen': [{'was': 'brep'|'fenster'|'zuordnung'|'kontext', 'grund', …}],
  'angenommen':    [{'primitiv', 'urteil_auf'} und je Regel Raster und Grenzwerte],
  'koerper':       {'<key>': hat_brep},          # vollständig, je Test
}
```

Kleinster Eingriff: `Result._publish()` bucht selbst (`results.budget_eintrag`). Die Körper
kommen aus `_common.as_bodies()` — der einzige Ort, an dem alle Primitive ihre Körper
durchreichen; `results.merke_koerper` / `zieh_koerper` reichen sie an das nächste `_publish`
weiter. Primitive ergänzen `result.uebersprungen` und `result.annahmen` (beides Eigenschaften,
keine Klassenattribute — eine Liste an der Klasse teilten sich alle Ergebnisse).

Körper ohne BRep werden **nicht** je Messung gemeldet, sondern einmal je Test als Sammelzeile
(`{'was': 'brep', 'anzahl': 102, 'keys': [...]}`). Je Messung wäre der Tray-Bericht 3 MB groß
und kein Mensch läse ihn.

Im Kopf des Berichts und als letzte Terminalzeile steht die Summe des Laufs
(`_budget_kopf`): Messungen, Körper, davon ohne BRep, Übersprungenes, Annahmen.

**`status: not_built_yet`** ist in `schrauben.yaml`, `schnittstellen.yaml` und `montage.yaml`
erlaubt (und nur dieser eine Wert, sonst fliegt der Lader). Die Anforderung bleibt in der Datei
stehen, die zugehörige Prüfung wird **unentschieden**: `interface_ok`, `screw_chain` und
`access` kehren sofort mit `results.ohne_urteil(...)` zurück, `Step.nicht_gebaut` sagt es für
einen Montageschritt. Grün wäre eine Aussage über Geometrie, die es nicht gibt.

### pytest-Plugin

- Registriert per Entry-Point `pytest11`. Konfiguration: `spec/pruefstand.yaml` neben den Tests:
  ```yaml
  machine: ../../rocking-photo-tray-r6d/machine/machine.json    # relativ zur yaml
  review: ../var/review                                          # optional, Default
  ```
- Fixtures (scope session): `project` (`.root` = Elternordner von `spec/`, `.spec`, `.review` angelegt),
  `machine` (geladen aus yaml).
- Marker `warnung`: ein Fehlschlag wird als **Warnung** gezählt (Outcome im Bericht `warnung`, pytest-Exit 0
  bleibt, Terminal-Zeile `W`). Umsetzung über `pytest_runtest_makereport` + `pytest_report_teststatus`.
- Bericht: `var/review/pruefstand.json` mit je Test: nodeid, outcome, dauer, aufgezeichnete Messwerte
  (`results.record`), `posen` und `budget` (siehe Prüfbudget oben); in der Wurzel `budget` als
  Summe des Laufs. Terminal-Summary: eine Zeile je Test mit den wichtigsten
  Messwerten (≤ 120 Zeichen), davor `~` bei angeschnittenem Fenster, hinter jedem Messwert
  `[brep]` / `[mesh]`.
- `posen`: die Posen, in denen gemessen wurde, als Liste von `State.as_dict()`. Ein Messwert
  ohne Pose ist bei bewegter Maschine nur die halbe Aussage — 0,2 mm Fuge bei Schwenk −135°
  und 0,2 mm bei +45° sind zwei Befunde. Eine **Liste**, weil ein Test mehrere Posen durchfahren
  darf; ein einzelnes Feld müsste sich für eine entscheiden.
  Erfasst wird an den zwei Stellen, an denen eine Pose überhaupt ins Spiel kommt:
  `State.apply()` (vor den Abkürzungen, damit auch die Vorgabepose zählt) und
  `_common.as_bodies()`, wenn dort eine `Scene` oder ein `at` ankommt — Szenen sind je Pose
  gecacht, beim zweiten Test mit derselben Pose läuft `apply` nicht mehr. `merke_pose`
  entdoppelt. Ein Test ganz ohne Maschinenpose hat `posen: []`, und das ist richtig so.
- `overlap` schreibt bei Kollision `pairs` **und** `contact_points` (Welt, mm, max. 64):
  im Netzweg die Kontaktorte aus fcl, im exakten Weg der Schwerpunkt des Schnittkörpers je
  Paar. Rechnet der Kernwächter, bleibt die Liste leer — der Rechenprozess liefert nur eine
  Zahl zurück, und einen Ort zu erfinden wäre schlimmer als keiner.
- `xfail(strict=True)`-Tests bleiben normales pytest-Verhalten (Rückbau-Prüfungen).

### Kernwächter `kernel.py`

Zuschaltbar über `PRUEFSTAND_KERNWAECHTER=1`. Booleans laufen dann in einem eigenen Prozess
(`spawn`; `fork` verklemmt sich auf macOS mit OCCT). Transport ist BREP, nicht pickle —
build123ds Pickle-Rückweg scheitert an echten STEP-Körpern, schreibt die Bytes aber klaglos.
Ein Absturz des Kindes wird zu `KernelFehler('Kernel abgestürzt, Signal SIGSEGV')` und damit
zu einem technischen Fehler; danach ist der Wächter wieder rechenfähig. Gemessen an einem Teil
mit 87 Flächen: 0,97 s für den ersten Aufruf inklusive Prozessstart, 6,8 ms je weiterem.
Deshalb nicht der Standard: die meisten Kernfehler werfen, und das fangen die Primitive selbst.

### Kollisionskern `_fcl.py`

- `bvh(mesh) -> fcl.BVHModel` gecacht je Body (id + Transform).
- `distance(mesh_a, mesh_b) -> (d, pa, pb)`, `collide(mesh_a, mesh_b) -> (n_contacts, max_depth)`.
- Meshes werden **nicht** prozessiert (process=False beim Laden), Watertightness nur gemeldet.

## Machine R6d bauen

`step-feeder/rocking-photo-tray-r6d/machine/build_machine.py`: ruft `Machine.from_manifest` mit
`../local/manifest.json`, Frame `local` (siehe oben), Motion `hub` 0…130, schreibt `machine.json`
(Dateien referenzieren `../local/<key>.stl`, nichts kopieren). Rolle aus Manifest übernehmen.
Hinweis in `source.note`: „STL-Tessellation aus dem nativen R6d-Studio, kein STEP-Export
(Onshape-Budget); STEP-Kontext nachziehen, wenn Budget frei ist."

## Abnahmekriterien

1. `uv run pytest tests -q` im Paket grün: Unit-Tests der Primitive an synthetischen build123d-Körpern
   (zwei Würfel mit 0,5 mm Spalt → gap 0,5; überlappend → overlap-Volumen exakt; Platte mit Loch →
   coverage open == Lochpunkte; Quader in Keep-out → protrusion; verschobene Kopie → same_as Abweichung).
2. Beide Referenz-Specs grün, die `xfail(strict=True)`-Varianten rot (also XFAIL, nicht XPASS).
3. Laufzeit je Spec < 3 min auf dem Mac (M-Serie). Wenn nicht: Vorfilter, nicht Toleranzen.
4. `var/review/pruefstand.json` und `coverage-*.png` liegen in beiden Projekten.
5. Keine Änderung an cad-khana, keine Änderung an den Referenztests (außer Fable gibt sie frei).
