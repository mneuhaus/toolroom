# Prüfstand — Etappe 4: Form (Absätze, Kerben, Rundungen) und Prüfbudget

Stand 18.09.2026. Auftrag für einen Opus-Subagenten; Fable nimmt ab. Vorher lesen: `HANDOFF.md`,
`SPEC.md`, `PLAN-etappe3.md` samt `var/etappe3-bericht.md` (so sieht ein abgenommener Auftrag
aus), `docs/konzepte.md`, `docs/fallstricke.md`. Referenzteile: Wanne `T01` aus
`step-feeder/rocking-photo-tray-r6d-tray-r1/native/tray-r1-native.step` (BRep) und Hopperboden
`T05` aus `step-feeder/rocking-photo-tray-r6d-hopper-floor-r1/native/hopper-floor-r1-native.step`.
`T41L/R` liegen im Maschinenkontext **nur als STL** — dafür gibt es in dieser Etappe keinen
BRep-Test; nicht exportieren (kein Onshape).

## Regeln (unverändert)

Kein Onshape-Aufruf. `uv run python` / `uv run pytest`, nie `python3`. Toleranzen nie lockern:
Messwert melden, `xfail(strict=True)`. Kein Git, keine `_v2`-Dateien. Stil der vorhandenen Dateien.
Ausgangsstand: Prüfstand **243 passed**, Tray **69 passed, 1 xfailed**, Hopperboden **23 passed,
2 xfailed** — nichts davon darf kippen; alle drei Läufe nach jedem Block. Nicht parallel laufen lassen.

## Warum

Marc am 17.09.: Die Stilregeln (keine Kerben, saubere Übergänge, R4,2 an Außenkanten, 0,42 mm
Bahnbreite) stehen in den Designregeln, werden aber nicht durchgezogen, weil niemand jedes
Teil danach absucht. Das Bild `docs/bilder/t41-absaetze-marc-2026-09-17.png` zeigt, was er
meint: Pfeile auf Absätze in der Seitenplatte T41 — Konturversätze von 1–3 mm, weil Blöcke
zusammengefügt wurden, statt die Kontur durchzuziehen. „Unnötige Shapes statt eines homogenen
Bodies." Das ist messbar, und zwar rein im BRep ohne Messfenster (also ohne die Fenster-Falle).

Alles in dieser Etappe sind **Warnungen** (`@pytest.mark.warnung`), keine Fehler. Ästhetik
im Sinne von „stimmig" bleibt Marcs Urteil; hier geht es um „sauber".

## Aufgaben

### 1. `form.py`: Kantenklassifikation als Grundlage

`src/pruefstand/form.py`, Funktion `kanten(body) -> list[Kante]` über
`TopExp.MapShapesAndAncestors_s(…, TopAbs_EDGE, TopAbs_FACE)`: je Kante Länge, Geometrietyp,
Knickwinkel, **konvex/konkav** (Vorlage: Fables Sonde — Mittelpunkt der Kante, Normalen beider
Flächen dort, Schwerpunkt der zweiten Fläche relativ zur ersten Normalen entscheidet die
Konkavität; an der Wanne: 79 Kanten, 11 konkave Geraden, 16 konvexe ~90° unverrundet, 0 Splitter).
Nur Körper mit `solid`; bei Mesh-only → `unentschieden` mit Grund „kein BRep".

### 2. `absatz(body)` — Marcs Bild

Ein Absatz ist ein Kantenpaar konvex + konkav, parallel (< 2°), Abstand 0,3–3 mm, mit einer
gemeinsamen schmalen Fläche dazwischen, deren Breite kleiner ist als ihre Länge, und deren
beide Nachbarflächen (fast) koplanar oder (fast) parallel liegen. Ergebnis `AbsatzResult`:
Liste `{ort (Welt), versatz_mm, laenge_mm, flaechen}`, `anzahl`. Test synthetisch (zwei
Quader um 1,5 mm versetzt vereinigt → 1 Absatz je Seite; bündig → 0) und an der Wanne
(erwartet 0 — steht so im Test, Messwert wird berichtet, wenn nicht).

### 3. `kerbe(body, kontext, at=None)` — Lücke ohne Anker

Konkave Kanten (> 60°), von deren Mittelpunkt entlang der Flächennormale eine Gegenwand des
**eigenen** Körpers in 0,2–2,5 mm liegt (Strahl im BRep über `BRepIntCurveSurface_Inter`
oder auf dem Mesh mit trimesh, dann `urteil_auf='mesh'`), gebündelt zu Zonen (5-mm-Raster).
Eine Zone ist erklärt, wenn ein Kontextkörper (Scene über alle Posen) oder eine Schraube aus
`schrauben.yaml` innerhalb 2,5 mm liegt, oder sie in `spec/form.yaml` unter `erklaert:` steht.
Unerklärte Zonen werden gemeldet mit Spaltbreite, Länge, nächstem Fremdkörper und dessen
Abstand. Fables Mesh-Sonde an T41L als Erwartungsbild: 544 mm enge Kanten, davon mit
Partner in 0,6–2,2 mm (T40L, R18, R59, T05) erklärt; unerklärt ~0,95 mm bei Y 135/155 nahe
der Pivotachse (nächstes Teil 15 mm) und 0,29 mm bei Z 265 (27 mm). Referenztest an T01
(erwartet 0 unerklärt) und T05.

### 4. `unverrundet(body, pose=None)` — R4,2-Regel

Konvexe Kanten mit Knick 80–100°, länger als 5 mm, die **Außenkanten** sind: beide Flächen
liegen auf der Hülle (Strahl von der Kante nach außen entlang der Winkelhalbierenden trifft
den eigenen Körper nicht). Wenn `teile.yaml`/Druckpose eine Auflagefläche nennt, sind Kanten an
der Bettseite ausgenommen (dort wird ohnehin nicht gerundet). Ergebnis: Liste + Gesamtlänge.
An der Wanne: 16 Kandidaten — die stehen als Befund im Bericht, Marc sagt, welche Absicht sind.

### 5. `splitter(body)` — Spuren von Block-auf-Block

Kanten < 0,42 mm, Flächen < 1 mm² zwischen Nachbarn > 100 mm², kollineare Nachbarflächen
mit Knick < 0,5° (nicht verschmolzen). Nur BRep. Wanne: 0/0/0 erwartet.

### 6. Prüfbudget im Bericht (aus CADCLAW adaptiert)

Jeder Testeintrag in `var/review/pruefstand.json` bekommt `budget: {geprueft: [...],
uebersprungen: [...], angenommen: [...]}` — was die Primitive tatsächlich gemessen haben
(Primitiv, Körper, Pose), was sie ausgelassen haben (Mesh-only-Körper, leere Fenster,
Bbox-Vorfilter-Ausschlüsse) und welche Annahmen galten (`urteil_auf`, Abtastdichte,
`rand_unschaerfe_mm`). Ein Bericht-Kopf summiert es je Lauf. Kleinster Eingriff über
`results.record`; in `SPEC.md` beschreiben. Dazu in den Pflegedateien (`schrauben.yaml`,
`schnittstellen.yaml`, `montage.yaml`) ein erlaubter Eintrag `status: not_built_yet`, der
den zugehörigen Test als `unentschieden` (nicht grün, nicht rot) ausweist.

### 7. Doku und SPEC

`docs/konzepte.md` Kapitel „Form" mit Marcs Bild, `docs/primitive.md`, `SPEC.md`-Verträge für
1–6. Jeweils mit Zahlen aus den echten Läufen.

### Ausdrücklich nicht

Kein Mesh-Splitter-Test (54 % Winzdreiecke allein durch Tessellierung — sinnlos). Kein
STEP-Export von T41. Keine Ästhetik-Heuristik jenseits der fünf Regeln. Kein UNSUPPORTED,
keine Toleranz-Taxonomie.

## Abnahme (Fable)

Drei Läufe grün (nur mehr Tests), `var/etappe4-bericht.md` im Format von Etappe 3: Summen aus
dem letzten echten Lauf, jeder Befund mit Ort und Messwert, jede Lesart-Entscheidung, was
nicht gemacht wurde. Fable liest die Befundlisten an Wanne und Hopperboden selbst.
