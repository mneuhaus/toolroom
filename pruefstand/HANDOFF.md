# Prüfstand — Handoff für die Implementierungs-Session

> **Stand 19.09.2026:** Etappen 1–5 sind gebaut und abgenommen (Suite 298 passed; Berichte in `docs/berichte/`,
> Pläne `PLAN-etappe3.md`/`PLAN-etappe4.md` sind erledigt). **Kein weiterer Ausbau geplant.** Marcs Urteil
> 18.09.: der Mehrwert ist offen; bewährt haben sich `access`, posiertes `overlap`/`gap` und `absatz`
> (siehe `../knowledge/workflow/offline-verification.md`). Der Prüfstand läuft ab jetzt nur nebenbei am
> nächsten echten Teil mit. Bekannte offene Werkzeugfehler: `overlap` meldete 2 090 mm³ Durchdringung als
> „touching" (SC15-Adapter R1, im Spec per Manifold gegengeprüft) — ungefixt.

Stand 17.09.2026, abgestimmt mit Marc am Ende der R6d-Session. Diese Datei ist der Auftrag für eine **frische Session**: lesen, dann bauen. Hintergrund in den Memories `cadspec-plan`, `delegation-preference`, `cad-design-preferences`.

## Entscheidungen (Marc hat genickt)

- **Name:** `pruefstand` (Paket, CLI und Ordner). Arbeitsname „cadspec" ist gestrichen.
- **Eigenes Paket** unter `toolroom/pruefstand/`, nutzt cad-khana als Bibliothek (Assertions, Wandstärke, Überhang, Zeichnungen), erweitert es nicht.
- **Tests sind pytest**, kein Gherkin. Lesbar durch eine kleine Fixture-/Helfer-Schicht, nicht durch eine eigene Sprache.
- **Kontext je Maschinenrevision:** einmal STEP-Export der ganzen Onshape-Baugruppe über die Bridge, daraus `machine.json` (Körper, Posen, bewegt/fest, Bewegungsdefinitionen, Vorgängerteile). Tests rufen Onshape nie auf.
- **Fehler gegen Warnung:** Geometrie, Schrauben, Werkzeugzugang, Montage-Sweeps = Fehler (blockieren das Slicen). Druckpose, Stabilitätsindex, Style = Warnung (Marker `@warnung`), im Bericht sichtbar.
- **Pflegedateien** (Schraubenliste, Montage-Storyboard, Druckposen und Lastabschnitte je Teil) pflegt das LLM selbst aus dem Gespräch heraus, laufend und korrigierend. Marc liest, schreibt sie nicht.
- **Arbeitsteilung:** Fable entwirft Primitive, Schnittstellen und die zwei Referenztests; ein Opus-Subagent implementiert nach Spezifikation; Fable nimmt ab (Renders selbst ansehen).
- **Kein Onshape-Budget verbrauchen.** GET features und FS-Eval haben 100/Tag; der Prüfstand arbeitet ausschließlich auf STEP.

## Projektlayout (gegen das Chaos, an Symfony/FHS angelehnt)

Jedes CAD-Projekt bekommt dieselbe Struktur; bestehende Projekte werden bei der nächsten Berührung migriert, nicht auf Vorrat.

```
<projekt>/
  README.md            Ergebnis für Marc (Konzept, Prüfungen, Druck, Montage, Offen)
  WORKING.md           Arbeitsnotizen, Fallen, Verlauf
  src/                 Quellen: make_fs.py, *.fs, pipeline.py, build_native.py, make_assembly.py
  spec/                vom LLM gepflegte Beschreibungen + Tests
    teile.yaml           je Druckteil: Druckpose, tragende Abschnitte (Achse, Lastart), Profil
    schrauben.yaml       je Schraube: Typ, Länge, Kette der Teile, Zugangsrichtung, Werkzeughülle
    montage.yaml         Storyboard: Schritt, Teil, Richtung, Weg, bereits montierte Teile
    test_*.py            pytest gegen var/step + machine
  var/                 regenerierbar, nicht in die Doku verlinken
    native/              state.json, API-Snapshots, STEP-Exporte
    review/              Prüfdaten (json), Karten (png), Logs
    print/               posed STL, Platten-3MF, Jobs, Slicer-Pakete, Slice-Logs
  dist/                Abgabe: finale 3MF, die zwei bis drei Bilder, die das README zeigt
```

Maschinenkontext liegt einmal je Revision außerhalb der Teilprojekte: `step-feeder/rocking-photo-tray-r6d/machine/` mit `machine.step` und `machine.json`. Teilprojekte referenzieren ihn, kopieren nichts.

## Primitive (erste Ausbaustufe)

Alle auf STEP + machine.json, exakte Booleans über build123d, Kollisionskern `python-fcl` für Sweeps.

| Primitive | Frage | Heutige Vorlage |
|---|---|---|
| `gap(a, b, at=hub)` | Mindest-/Sollabstand, Kontaktzonen ausnehmbar | Schnitt-Messungen Hopperboden |
| `overlap(a, b)` | Überschneidungsvolumen, erwarteter Wert (z. B. Schaft im Pilot) | check_geometry der vier R1-Projekte |
| `coverage(teil, region, richtung)` | Strahltest, Start außerhalb aller Körper, offene Fläche | Hopperboden coverage.png |
| `protrusion(teil, volumen)` | nichts steht in ein Volumen vor | Schale „innen eben" |
| `same_as(teil, vorgänger, region)` | Region geometrisch unverändert | Hopperboden Rückwand |
| `sweep(teile, vektor, weg, gegen)` | Bewegung kollisionsfrei | R6d check_mesh_motion.py, check_access.py `path()` |
| `access(schraube)` | Werkzeughülle von außen bis zum Kopf frei | R6d check_access.py (Hüllen Ø5,7 M3, Ø8,5 M5, Schaft Ø4,8 × 112, Griff Ø18 × 55) |
| `screw_chain(schraube)` | Kopf → Durchgang Ø3,4 → Pilot Ø2,62 oder Crush-Grip Ø4,2 + 3 Rippen, nur letztes Glied beißt, Einschraubtiefe, Restwand | cad-design-preferences (M3-Tabelle) |
| `print_pose(teil)` | Auflage, Überhang > 50°, Brücken, Bett 250 × 250 | prepare_print.py der R1-Projekte, fusion-khana sliceability |
| `stability(abschnitt)` | Index aus wirksamem Querschnitt × cos²θ | Memory cadspec-plan |
| `relevance(teil, kontext)` | hängt jedes Stück Material an einem Anker oder auf einem Lastpfad zwischen zwei Ankern? | Marcs Befund 17.09.2026: nach Schnitten bleiben Zipfel ohne Funktion stehen |

`relevance` ist eine **Warnung**, kein Fehler. Anker sind Nahfeld/Kontakt zu anderen Körpern über **alle** Posen (Standard < 1,0 mm), Bohrungsränder, und explizit in `relevanz.yaml` erklärte Bereiche. Material, das weder in Ankernähe liegt noch zwei Anker verbindet, wird als zusammenhängende Insel mit Volumen und Ort gemeldet. Das eigentliche Risiko sind Falschmeldungen — lieber konservativ melden als jeden gesunden Steg anmahnen.

Stabilitätsindex: wirksamer Querschnitt aus Profil (Wände × 0,42 mm, Infill-Dichte, **Standard 25 %**), nicht Vollmaterial. Anker Ø10 rund senkrecht = 1,0 = K.o.; Schwellen vorläufig < 1,5 Fehler, 1,5–4 Warnung; nach vier Probestäben (Ø10/Ø20 senkrecht, Ø10 45°, Ø10 liegend) festziehen. Zuschläge: Kerbe am Fuß, durchgehende Schichtfuge im dünnsten Querschnitt.

## Reihenfolge

1. Paketgerüst, `machine.json`-Importer, STEP-Loader, `gap/overlap/coverage/protrusion/same_as`.
2. Referenzfälle: Hopperboden R1 und Riemenklemme R1 als `spec/test_*.py`, aus den vorhandenen `check_geometry.py` übersetzt. Beide müssen grün sein und die heute bekannten Fehler (Lücke, Klotz innen, Hebel-Durchdringung) bei absichtlichem Rückbau rot melden.
3. `screw_chain` und `access` mit `schrauben.yaml`; `sweep` mit `montage.yaml`.
4. `print_pose`, dann `stability`, Probestab-Platte für Marc.
5. `pipeline.py`-Muster: bauen → STEP → pytest → bei grün slicen; Subagent-Lauf, im Hauptkontext nur die pytest-Zusammenfassung.
6. Style-Warnungen zuletzt (Kerben ohne Verrundung, dünne stehende Rippen, fehlender Kantenbruch).

Parallel dazu, weil sie an eigenen Nähten liegen und nichts blockieren: `relevance`, der HTML-Bericht mit
3D-Viewer (`report/`, liest `var/review/pruefstand.json`) und die anschauliche Doku unter `docs/`.

## Token-Regeln für die Session

Eine Session für Punkt 1–2, dann `/compact` oder neu. Renders auf Platte, ansehen nur bei Entscheidung. Große Ausgaben als Datei, im Terminal Kopfzeilen. Verbrauch prüfen mit `toolroom/scripts/usage_report.py 24 10`.
