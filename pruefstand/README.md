# pruefstand

pytest-Prüfstand für Onshape-native CAD-Teile: misst Spalte, Überschneidungen, Abdeckung,
Vorstehen und unveränderte Regionen gegen einen Maschinenkontext aus STEP/STL + `machine.json`.
Kein Onshape-Zugriff, alles läuft auf Dateien. Längen in mm, Volumen in mm³.
Schnittstelle und Abnahmekriterien: `SPEC.md`, Hintergrund: `HANDOFF.md`.
Erklärte Doku mit Bildern, Beispielen und Fallstricken: [`docs/README.md`](docs/README.md).

## Einrichten

```bash
cd toolroom/pruefstand && uv sync        # ocp-gordon==0.2.0 ist Pflicht, sonst bricht OCP
uv run pytest tests -q                   # Unit-Tests der Primitive
```

`python3` ist im Shell-Profil umgebogen: immer `uv run python …` / `uv run pytest …` benutzen.

## Ein Projekt prüfen

```bash
uv run pytest ../../step-feeder/rocking-photo-tray-r6d-hopper-floor-r1/spec -q
# oder
uv run pruefstand run ../../step-feeder/rocking-photo-tray-r6d-hopper-floor-r1
```

Neben den Tests liegt `spec/pruefstand.yaml` (Pfade relativ zur yaml):

```yaml
machine: ../../rocking-photo-tray-r6d/machine/machine.json
review: ../var/review        # optional, Default <projekt>/var/review
```

Das Plugin stellt die Session-Fixtures `project` (`.root`, `.spec`, `.review`) und `machine`.
Marker `@pytest.mark.warnung` macht aus einem Fehlschlag eine Warnung (Terminal `W`, Exit-Code 0).
Nach dem Lauf stehen alle Messwerte in `<projekt>/var/review/pruefstand.json`,
Abdeckungskarten in `coverage-<test>.png`.

## Maschinenkontext bauen

`machine.json` (Schema `pruefstand.machine/1`) entsteht aus dem Körper-Manifest einer Revision:

```bash
uv run python ../../step-feeder/rocking-photo-tray-r6d/machine/build_machine.py
```

Das Skript ruft `Machine.from_manifest(...)` mit Frame `local` (25°-Kippung, Ursprung Z 203)
und Motion `hub` 0…130 mm. Die Körper werden als `../local/<key>.stl` referenziert, nichts kopiert.

## Primitive in fünf Zeilen

```python
gap(a, b, at=None, within=None, ignore=None)        # kleinster Abstand (fcl), .min_mm / .per_body
overlap(a, b, at=None, within=None)                 # exaktes Schnittvolumen oder fcl-Kollision
coverage(by, region, direction, at=None)            # Strahltest je Abtastpunkt, .open / .map_png
protrusion(part, volume, at=None)                   # Material in einem Sperrvolumen, .volume_mm3
same_as(part, predecessor, region, at=None)         # Region unverändert, .max_deviation_mm
```

`a`/`b` nehmen einen `Body`, eine Liste oder eine `Scene`; `at=machine.state(hub=…)` verschiebt
alle übergebenen Körper mit `moving=True` um die Motion. Regionen kommen aus
`Region.box / Region.points / Region.plane_grid` in einem `Frame` der Maschine.
Berührende Flächen (fcl-Kontakttiefe ≤ 1e-4 mm) gelten als Berührung, nicht als Durchdringung:
`result.touching` statt `result.collides`.
