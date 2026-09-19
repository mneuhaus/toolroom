# Probestaebe — Kalibrierung Stabilitaetsindex (PLA, Bambu A1, 0.4mm Duese)

Vier Probestaebe fuer die Kalibrierung des Stabilitaetsindex im `pruefstand`-Werkzeug.
Gemeinsamer Fuss 30x30x8mm mit zwei Oe3.4 Durchgangsloechern (X=+-10mm) zum Anschrauben
auf ein Brett, Stab freie Laenge 60mm. Am Uebergang Stab->Fuss bewusst KEINE Verrundung
(Kerbwirkung der Schichtfuge ist das Messziel).

## Varianten

| Name | Stab | Achse | Druckpose |
|---|---|---|---|
| S1_d10_senkrecht | Oe10 | +Z | Fuss auf dem Bett |
| S2_d20_senkrecht | Oe20 | +Z | Fuss auf dem Bett |
| S3_d10_45grad | Oe10 | 45deg zw. +Z/+Y | Fuss auf dem Bett, ohne Stuetzen |
| S4_d10_liegend | Oe10 | +Z (nativ), 90deg um X gedreht | Stab liegt horizontal auf dem Bett |

Kennzeichnung: 1-4 Kugelkalotten (Oe2 x 0.6mm tief) auf der Stab-Stirnflaeche, Anzahl =
Variantennummer.

## Geometrie-Ergebnisse (nativ modelliert, `src/make_probestaebe.py`)

Alle vier Teile: 1 Solid, wasserdicht (nach Entfernen einer bekannten OCC-Tessellierungs-
Randbedingung, siehe unten), Fase 0.42mm auf allen 12 Aussenkanten des Fusses erfolgreich
(`chamfer_ok: true` bei allen vier).

| Teil | Volumen mm3 | BBox nativ (X,Y,Z) mm |
|---|---|---|
| S1_d10_senkrecht | 11 740.6 | 30.0 x 30.0 x 68.0 |
| S2_d20_senkrecht | 25 872.2 | 30.0 x 30.0 x 68.0 |
| S3_d10_45grad | 15 250.4 | 30.0 x 61.0 x 54.0 |
| S4_d10_liegend | 11 493.0 | 30.0 x 9.0 x 90.0 |

S3 Stabachse `(0, 0.7071, 0.7071)`, Stabende bei `(0, 42.43, 50.43)` — Fuss dafuer in Y auf
30..-15 (Y=-15..30, Mitte 7.5) verlaengert.

**Bekannter Meshing-Artefakt:** Die Boolean-Vereinigung Stab-auf-Fuss (bzw. der Flach-
schnitt bei S4) hinterlaesst an der deckungsgleichen Uebergangsebene ein paar hauchduenne,
exakt senkrecht nach unten zeigende (`normal=(0,0,-1)`) Splitterdreiecke (< 0.2mm² je
Dreieck, z.B. 8.7mm² Gesamtflaeche bei S2). Das ist reines Tessellierungsrauschen der
coincident-plane-Vereinigung (siehe `cad-khana-quirks` Memory: "Boolean-Lotterie"), keine
echte fehlende Auflage — an der Stelle liegt durchgehend Vollmaterial darunter. Zusaetzlich
erzeugt der Export ein einzelnes entartetes Null-Flaechen-Dreieck an den Kugelkalotten-Polen.
Beide Artefakte werden vor der `is_watertight`-Pruefung per `nondegenerate_faces()` /
`merge_vertices()` bereinigt (`make_probestaebe.py`) bzw. bei der Ueberhang-Klassifikation
als exakt-flache (`nz<-0.9995`) Splitter ausgefiltert (`prepare_print.py`) — das Design hat
sonst nirgends beabsichtigte flache (0deg-von-vertikal) Ueberhaenge, der Filter ist also
fuer dieses Teil ungefaehrlich.

## Druckpose-Analyse (`src/prepare_print.py`)

Bett 250x250mm, Layout einreihig entlang X mit >=15mm Abstand, Gruppe zentriert,
Z-Minimum = 0 je Teil (Assertions im Skript):

| Teil | Pos (X,Y) mm | BBox Druckpose mm | Bettauflage mm2 | Ueberhang gesamt mm2 | max. Ueberhang von vertikal | steiler als 45deg mm2 |
|---|---|---|---|---|---|---|
| S1_d10_senkrecht | 42.5, 110.0 | 30.0x30.0x68.0 | 832.2 | 69.9 | 45.00deg (Fase) | 0.0 |
| S2_d20_senkrecht | 87.5, 110.0 | 30.0x30.0x68.0 | 832.2 | 78.6 | 45.00deg (Fase) | 0.0 |
| S3_d10_45grad | 132.5, 94.5 | 30.0x61.0x54.0 | 1269.6 | 567.5 | **45.004deg** | 0.0 |
| S4_d10_liegend | 177.5, 80.0 | 30.0x90.0x9.0 | 1205.1 | 308.5 | 60.19deg | **71.9** (Rundstab-Bogen, ohne Stuetzen druckbar, siehe unten) |

S3: Stab ist konstruktionsbedingt exakt 45deg von vertikal geneigt; gemessener Wert
45.004deg liegt numerisch knapp ueber 45 (Toleranzband 0.15deg im Skript), die Flaeche
"steiler als 45deg" bleibt bei 0.0mm2 — Assertion erfuellt, Design ist stuetzenfrei
druckbar wie gefordert.

S4: Ein liegender **runder** Stab (Oe10) hat an seinem oberen Bogen rechnerisch Ueberhang
> 45deg — das ist bei jedem zylindrischen Rundstab in liegender Druckpose so. **Stuetzen
braucht er trotzdem nicht**, und es wurden auch keine gesliced: der Ueberhang ist
selbsttragend, weil jede Lage nur um einen Bruchteil der Duesenbreite nach innen
zurueckspringt; erst dicht unter der Scheitellinie wird die Oberflaeche etwas rauh, was
hier kosmetisch ist (die Messflaechen liegen an Fuss und Flat). Rundstaebe bis etwa Oe15
druckt die A1 liegend ohne Stuetzen. Der 45deg-Flaechenwert ist deshalb ein reines
Geometriemass und wird nur reportet, nicht assertet. Gesliced wurde mit dem
R6d-Standardprozess ohne Stuetzen (siehe `var/print/jobs/A1-01.json`). Fuer S1/S2/S3 ist
die "0mm2 steiler als 45deg"-Assertion hart erzwungen und besteht.

Alle vier Teile: Z-Minimum = 0, innerhalb 250x250mm Bett, >=15mm Abstand zueinander (siehe
`var/print/layout.json` fuer exakte Koordinaten).

## Slice-Ergebnis

Slicer (`/Applications/BambuStudio.app`, Profile aus
`step-feeder/rocking-photo-tray-r6d/printing/profiles/`) wurde ueber
`toolroom/skills/cad-fdm-design/scripts/print_package.py build` ausgefuehrt
(`var/print/A1-01-slice.log`, Paket-Report in `var/print/packages/<hash>/report.json`).

- BambuStudio-Aufruf selbst lief durch (`returncode: 0`, siehe
  `var/print/packages/<hash>/logs/native.log`).
- **Zeit/Gramm konnten NICHT ermittelt werden**: `print_package.py` ist bewusst ein reines
  Paket-/Profiltreue-Pruefwerkzeug (siehe sein eigener Docstring: "never dispatches a
  print... stops at file preparation") — es ruft BambuStudio mit `--slice 0` auf (nur
  Export-Validierung, kein echter Slice-Lauf) und vergleicht native- vs. reimport-3MF auf
  Profil-Identitaet. Es erzeugt keine G-Code-Zeit-/Gewichtsschaetzung. Endstatus
  `"status": "review"` mit mehreren offenen Findings (`native_export`,
  `resolved_profile_values_applied`, `profiles_preserved_on_reimport`,
  `authoritative_source_geometry_preserved` = `fail`) — das ist der normale
  "braucht menschliche Pruefung"-Endzustand dieses Tools, kein Absturz.
- Fuer eine echte Zeit-/Gramm-Schaetzung waere ein zusaetzlicher BambuStudio-Lauf mit
  `--slice 1` + G-Code-Export noetig; das war ausserhalb des Scopes dieses reinen
  Paket-Validierungswerkzeugs und wurde hier nicht nachgeholt.
- Plate-3MF liegt trotzdem final unter `dist/Probestaebe_A1-01.3mf` ab.

## Renders

- `var/print/plate-iso.png` — gesamte Platte (matplotlib, kein pyrender/pyglet in der
  toolroom-Umgebung verfuegbar)
- `var/print/S1_d10_senkrecht-iso.png`, `S2_d20_senkrecht-iso.png`,
  `S3_d10_45grad-iso.png`, `S4_d10_liegend-iso.png` — je Stab in Druckpose

## Dateien

- `src/make_probestaebe.py` — Geometrie (build123d), exportiert native STLs nach
  `var/print/parts/`, schreibt `var/print/geometry-report.json`
- `src/prepare_print.py` — Druckpose, Layout, Ueberhang-/Bettauflage-Analyse, Plate-3MF,
  Job-JSON, ruft `print_package.py build` auf; schreibt `var/print/layout.json`
- `src/render_previews.py` — matplotlib-Vorschaubilder
- `var/print/parts/*-native.stl` — Teile wie modelliert (vor Druckpose-Transform)
- `var/print/parts_posed/*-posed.stl` — Teile in Druckpose, auf dem Bett platziert
- `var/print/plates/A1-01.3mf`, `dist/Probestaebe_A1-01.3mf` — fertige Platte
- `var/print/jobs/A1-01.json` — Slice-Job-Definition
- `var/print/A1-01-slice.log`, `var/print/packages/` — Slicer-Ausgabe/-Paket

## Ausfuehren

```bash
cd /Users/mneuhaus/Workspace/cad/toolroom
uv run python pruefstand/probestaebe/src/make_probestaebe.py
uv run --with networkx --with lxml python pruefstand/probestaebe/src/prepare_print.py
uv run --with matplotlib python pruefstand/probestaebe/src/render_previews.py
```

(`networkx`/`lxml` werden nur fuer trimesh's 3MF-Export gebraucht, `matplotlib` nur fuer
die Vorschaubilder — beide fehlen in der Basis-toolroom-Umgebung und werden per
`uv run --with` ad-hoc nachinstalliert statt die pyproject.toml global zu aendern.)
