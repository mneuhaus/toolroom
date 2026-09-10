---
name: fusion360
description: "Marcs Fusion-360-Workflow mit fusion-khana — Rebuild-from-source, Bilanz-Assertions, Ebenen-/Loft-DSL, Komponenten+Farben, Kanten-DSL, Konvexitäts-Klassifikator, Checks + Druckfreigabe-Tools (sliceability: OrcaSlicer-headless Support/Zeit/Auflage/Orientierungsvergleich; strengthcheck: Layer-Anisotropie/Schichtbruch). Laden BEVOR in Fusion 360 konstruiert wird ODER Druckbarkeit/Festigkeit von STLs bewertet wird (MCP-Server „fusion\" auf :27182 oder Direkt-HTTP). Companion zu onshape-cad/cad-fdm-design."
---

# Fusion 360 via MCP + fusion-khana

## Transport

- MCP-Server `fusion` (Streamable HTTP, `http://127.0.0.1:27182/mcp`) — Tools
  `mcp__fusion__*` (execute/read/update). Fusion-Desktop-App muss laufen.
- Fallback ohne registrierten Server: JSON-RPC direkt (initialize →
  `notifications/initialized` → `tools/call`); Helper `tools/fcall.py`
  (`uv run python fcall.py script <datei.py>` / `shot <out.png> [dir]`).
- `fusion_mcp_execute {featureType:"script", object:{script}}` führt Python im
  Fusion-Prozess aus: `def run(_context)`, prints = Tool-Output, Exceptions =
  Fehler mit Traceback. NIE Exceptions im Skript schlucken.
- **Fusion-Instanz ist SHARED + single-threaded:** Ein offener MODALER DIALOG
  (oder ein hängendes Cloud-`documents.open`) blockiert JEDEN Script-Call
  („Cannot perform 'script' while a command dialog is open" / Timeout). Nicht
  gegen die Wand pollen — Wächter mit `until … fcall … ; do sleep 120; done`
  im Hintergrund setzen und den User bitten, den Dialog zu schließen.

## Architektur: Rebuild-from-source (VibeCAD-Lehre)

Source of truth ist das Part-Programm in git — die Fusion-Timeline ist nur
publiziertes Ergebnis. **Kein Timeline-Gefrickel bei Änderungen: Programm
editieren, frisches Dokument bauen lassen.** Face-/Kanten-IDs sind damit
strukturell egal.

- Library: `~/Workspace/cad/fusion-khana/fusion_khana/` (eigenes git-Repo)
- Part-Programme: `~/Workspace/cad/fusion-khana/parts/<part>.py` mit
  `P`-Parameter-Dict + `build(k)` + `main()`. Gemeinsame Rahmen/Helfer in ein
  `<projekt>_common.py` faktorisieren, Varianten importieren daraus
  (BristleBot-Familie: `bristlebot_common.build_frame(k, P)` + variantenspez.
  Bauch). expect-Summen als `frame_expect(P)`-Funktion, nicht als Literal.
- **EIN stabiles Cloud-Dokument je Part-Programm**: `Khana(new_doc=...)`
  reused ein offenes Dokument gleichen Namens (leert es), statt Tabs
  anzusammeln; `k.accept("note")` speichert den GRÜNEN Build als Fusion-
  VERSION. Fehlgeschlagene Builds bleiben ungespeichert. Versionsnummer nie
  direkt nach save abfragen (Cloud-Save async → stale).
- **`direct=True` (DirectDesign)** setzen, sobald freie Ebenen/Loft gebraucht
  werden (`setByPlane` gibt es nur ohne Timeline). `_clear_design` ist
  timeline-safe (fängt `des.timeline`-RuntimeError) und räumt auch
  Konstruktionsebenen.
- Bootstrap: `tools/bootstrap.py` (PART-Konstante setzen, per
  fusion_mcp_execute schicken). **Fusion cached Module im Prozess — reload()
  reicht NICHT (transitive Imports parts→parts bleiben alt): alle Module mit
  BASE im `__file__` vor dem Import aus sys.modules werfen** (macht das
  Template).

## Montage, Druckvorbereitung und Ablage

- Bei geschraubten/beweglichen Baugruppen die
  [Montageprüfung](../cad-fdm-design/references/assembly-review.md) ergänzen:
  Schrauben einzeln einsetzen können, Werkzeugkorridore und Annäherungswege
  prüfen. Ein Interferenztest der Endlage allein reicht dafür nicht.
- Für Bambu Studio die [Profil- und Druckprüfung](../cad-fdm-design/references/bambu-preparation.md)
  lesen. Der unten genannte Orca/Voron-Ablauf ist ein vorhandenes Beispiel;
  Drucker, Material und Platte aus dem aktuellen Auftrag wählen.
- Für länger laufende Projekte [Projektablage](../cad-fdm-design/references/project-layout.md)
  nutzen; bestehende Bibliotheks-/Importpfade bei einer Umordnung mitziehen.

## Pflicht-Loop (Onshape-Disziplin, hier erzwungen)

1. Jede Volumen-Op bekommt `expect=<mm³>` — vorher VORRECHNEN. Bei Abweichung
   wirft `BalanceError` mit Kontext; Toleranzen: Extrudes 0,5, Fillets/Fasen
   1,5–3, Lofts 5–18 (Sektions-Interpolation). Text-Gravur ist NICHT
   vorhersagbar (Font-Mikrokeile) → `k.text()` prüft bewusst kein expect.
2. **Die Bilanz fängt echte Fehler, nicht nur Tippfehler** — diese Session:
   Poke unter Rundkanal ist ein SATTEL, kein Flachring (`poke_expect`-Integral);
   Fuß-Spalt-Soll brauchte Trapezregel statt Rechteck (−9 mm³/Bein);
   Rast-Nase am Heck füllte still das Schalterfenster wieder auf (+2 mm³).
   Bei Abweichung erst die GEOMETRIE-Annahme prüfen, nicht nur die Toleranz.
3. Ende jedes Programms: `check_total` (bzw. Wannen-Volumen bei Referenzteilen
   im Dokument), `check_interference` (über `all_bodies`), `check_clearance`
   (Fugen ≥0,19), `check_bed` (250×250), gezielter `export_stl(dir, bodies=…)`.
4. Extern gegenprüfen: trimesh-Diff (sample + closest_point BEIDSEITIG) gegen
   Onshape. **`tessellatedfaces?chordTolerance=` ist in METERN** (0,02 mm =
   `0.00002`); ≤0,2 mm Diff = Tessellationsrauschen, mehr = fehlendes Feature.
   Diff braucht `trimesh` + `rtree`; Onshape-Mesh in m → ×1000.
5. Druckbarkeit vor Druckfreigabe: `uv run tools/sliceability.py <stl…>`
   — vorhandener CLI-Standard: OrcaSlicer mit Voron-Presets; für andere
   Drucker/Bambu Studio zuerst Binary und tatsächliche Profile anpassen. Zeit/Gewicht/
   Support-%/max-Bridge-Spannweite/Bettauflage-% („LIEGT NICHT SATT"-Warnung).
   `--compare` prueft as-is vs flip-x180 (Flip via trimesh-Temp-STL — Orcas
   eigene --rotate-x/--ensure-on-bed-Flags CRASHEN mit gefalteten Profilen!),
   `--map DIR` schreibt Overhang-Karten-PNGs (Unteransicht, blau=Bett,
   rot=flach haengend). **„Druckebene zuerst"**: die Bett-Ebene ist eine
   DESIGN-Entscheidung pro Teil (nichts darf drunter rausstehen; sonst Teil
   anders teilen + verschrauben) — siehe cad-design-preferences-Memory.
6. Struktur-Check: `uv run tools/strengthcheck.py <stl…>` — Layer-
   Anisotropie via Z-Querschnitts-Sweep in Drucklage (A(z), Wx/Wy(z),
   Insel-Zerfall): meldet EINSCHNUERUNGEN (Sollbruchstelle an der
   Schichtnaht), Aufsätze mit dünner Layer-Anbindung (z-Zug an Pads =
   Schichtnaht-Zug ~50 %), SCHLANK-HOCH (stehender-Stab-Risiko).
   `--compare` (as-is/flip), `--plot DIR` (A/W-Kurven-PNG). Analytisch am
   Balken validiert (W = b·h²/6 exakt). Kein FEM — Geometrie-Heuristik.
7. Screenshot via `fcall.py shot` bzw. `fusion_mcp_read {queryType:
   "screenshot"}`. **VORSICHT SHARED-Instanz:** der Shot erwischt das gerade
   AKTIVE Dokument — bei Parallel-Session ggf. das falsche. STL-Diff/lokales
   trimesh-Rendering ist der belastbare Beweis, nicht der Screenshot.

## fusion-khana API (Kurzreferenz)

Alles in **mm**, Welt-Frame wie die Onshape-Projekte. `k = Khana(new_doc="…",
direct=True)`.

- **Sketch auf Ebene** `k.sketch(name, plane="xy"|"xz"|"yz")`. ALLE Sk-
  Koordinaten sind WELT-Paare der Ebene (xy→(x,y), xz→(x,z), yz→(y,z)); intern
  `modelToSketchSpace` — **das entschärft den xZ-Spiegel-Quirk strukturell,
  kein Vorzeichen-Raten mehr.** Primitive: `.rect(x0,y0,x1,y1)`,
  `.circle(x,y,d)`, `.circles(pos,d)`, `.polyline(pts, close=True)`,
  `.rounded_rect(...)` (nur xy).
- **Extrude** — Fenster `[w0,w1]` läuft entlang der Ebenen-NORMALE (xy→z,
  xz→y, yz→x), Vorzeichen über die echte Sketch-Weltnormale aufgelöst:
  `k.new_body(sk, w0, w1, name, expect=)`, `k.cut(sk, w0, w1, [bodies], name,
  expect=)`, `k.join(...)`. Participants IMMER setzen.
- **Freie Ebene + Loft** (Sektionen quer zu Pfaden, z. B. Fuß-Spalt entlang
  einer Sinuslinie): `sk = k.sketch_free(name, origin, normal)` +
  `sk.poly3(world_pts)`; dann `k.loft_cut([sk0,sk1,…], [bodies], name,
  expect=)`. Braucht `direct=True`. Sektion 1–2 mm über die Spitze
  hinaus verlängern (nie am freien Pfadende enden = Zacken).
- **Komponenten** (saubere Struktur + kein Auto-Merge): `with
  k.component("Wanne X"):` baut Sketches/Bodies in eine benannte Sub-
  Komponente. **Pflicht für Referenz-Dummies** — ein `new_body`, der in einer
  engen Tasche/auf einer Fläche eines Nachbar-Bodies entsteht, VERSCHMILZT im
  DirectDesign sonst STILL mit ihm (Mini-Motor-Dummy → Wanne). `k.all_bodies()`
  sammelt über Wurzel + alle Occurrences (Interferenz/Report/Export).
- **Farben** `k.color(body, "petg"|"pcb"|"gold"|"silber"|…|(r,g,b))` — Matte-
  Plastic-Appearance mit Custom-Color (addByCopy von „Plastic - Matte (Gray)"
  aus „Fusion Appearance Library", ColorProperty „Color"). Palette in `_RGB`.
- **Text gravieren** `k.text(s, box=(x0,y0,x1,y1), z_top, depth, [bodies],
  name, height=)` — SketchText direkt als Extrude-Profil (NICHT `sk.profiles`,
  die sind bei Text leer). Kein expect.
- **Render-Hygiene** `k.hide_construction()` blendet Sketches+Ebenen aus.
- **Kanten** `k.edges_flat_at(z)`, `k.edges_vertical_at(ecken)`,
  `k.is_convex(edge)` (orientierungsfreier Dieder-Test via Sehnen-Mittelpunkt
  → pointContainment; Bisektor-Tests FUNKTIONIEREN NICHT).
- **Stil** `k.fillet(coll, r, name, expect=)`, `k.chamfer(coll, d, name,
  expect=)`, `k.chamfer_flat_convex(z)` (fast konvexe Kanten der Ebene,
  überspringt Kerben, loggt sie). Noppen-Kopffasen: `edges_flat_at(top)` +
  `chamfer` (findet die Kappen-Kanten auch nach dem Union).
- **Referenzteile** — fertige Zukaufteile NICHT im Druck-Programm
  nachmodellieren, sondern als Dummies/Envelopes in ein `<projekt>_ref.py`
  (Envelope-Philosophie: strikte Obermenge → jede bestandene Clearance gilt
  auch real), in situ platzieren, einfärben, in `k.component("Referenz")`.
  `k.import_body(doc_prefix, matrix, name)` kopiert einen Body aus einem
  OFFENEN Dokument (TemporaryBRep + Transform) — nutzbar, aber Cloud-`open`
  hängt chronisch; eine aus Messwerten GEZEICHNETE Referenz ist robuster.
  `k.import_step(path)` sammelt Bodies rekursiv aus STEP-Sub-Occurrences.
- **Kinematik** `k.sweep_check(moving, statics, [(dx,dy,dz)…])` /
  `k.check_sweep_free(...)` — bewegte Teile gegen ALLE Hubpositionen, plus
  IMMER ein Negativ-Test jenseits des Anschlags (beweist Check-Sensitivität).
- **Makros** `puzzle_seam_profile(sk, x_line, tab_dir)`, `pt_axis(k, pos,
  z_top, z_seam, top_body, bottom_body)`.
- **Loft/Spline/Shell** `sk.spline(pts)` / `skfree.spline3(world_pts)` /
  `skfree.circle3(centre_world, d)` (gefittete Splines, `isClosed`),
  `k.loft(sections, name, op="new"|"join"|"cut", bodies=…, expect=)` — jede
  Sektion MUSS genau ein Profil liefern (sonst ist die Kontur offen; die
  Library wirft mit Sektionsnamen). `k.shell(body, faces, t, name)` hoehlt nach
  innen. Flaechen/Kanten geometrisch picken: `k.face_planar_at(body, "x", 126)`,
  `k.faces_planar_at(...)`, `k.edges_planar_at("x", 0.0)` (verallgemeinert
  `edges_flat_at`, das nur z konnte).
- **Report/Export** `k.report()` (über all_bodies), `k.export_stl(dir,
  bodies=[…])` (MeshRefinementHigh), `k.save(name)`, `k.accept(note)`.

## Maße messen / verifizieren

- **Vendor-CAD schlägt Shop-Fotos**: SLDPRT/STEP in die Cloud laden
  (`folder.uploadFile`, `uploadState`-Poll), Body-BBox/Polar-Kontur abtasten.
  So kam heraus, dass der LilyPad DEV-13883 32,4×30,2 misst (Näh-Laschen
  überragen den Ø29-Kreis) — die Foto-Schätzung 28×29 war 3 mm zu schmal.
- Geschätzte Maße (aus Fotos) im Programm-Docstring als „VORBEHALT —
  nachmessen" markieren; im P-Dict einzeilig korrigierbar halten.

## Fusion-Quirks (ergänzt [[fusion-mcp-quirks]]-Memory)

- API-Einheit cm — die Library kapselt das; in rohen Skripten ×0,1 denken.
- `chamferFeatures.createInput2` + `addEqualDistanceChamferEdgeSet(…, False)`;
  `filletFeatures.createInput().edgeSetInputs.addConstantRadiusEdgeSet(…,False)`
  — isTangentChain=False, sonst laufen Ketten weiter.
- **Fusion-Fillet verweigert Overflow-Rundungen** (r > Stegbreite,
  `ASM_ABL_CAP_COMPLEX`, z. B. auf einer 0,9er-Zunge) → Fillet als Viertel-
  kreis-Cutter-GEOMETRIE bauen (`round_cutter_pts`), der Nachbar-Cut trimmt
  ihn wie das Kernel-Fillet.
- **UI-nachgetragene Onshape-Features fehlen im FS-Quelltext** — beim Nachbau
  per Mesh-Schnitt (tessellatedfaces) aufdecken (Wulst-r1,2 der Flach-Wanne).
- Cut, der einen Body teilt → sauber 2 Bodies; danach `body.name` nach Lage.
- STL-Export MeshRefinementHigh; Onshape-STLs kommen in METERN, Fusion in mm.

## Referenz-Piloten

- `parts/cff12_plattform_v7.py` — bitgenau gegen Onshape (1 654 611 mm³,
  STL-Diff ≤0,17). Timeline-Pilot.
- `parts/bristlebot_*.py` — Familie aus gemeinsamem Rahmen
  (`bristlebot_common`) + Varianten (flach/torpedo/mini/gen2) + parametrischem
  Deckel + Referenzteilen (`bristlebot_ref`) in Komponenten mit Farben. Zeigt
  Ebenen-Sketches, Loft, direct=True, Komponenten, Farben, Text, in-situ-Refs.
- `parts/lego_studcal.py` — Noppen-Kalibrierstreifen (2×2-Blöcke, Text-Gravur).

## Noch nicht gebaut (geplante Ausbaustufen)

- Scan-Mesh-Import als Referenz-Body (Passung gegen echte Scan-Geometrie).
- Overhang-/Wandstärken-Printability wie cad-khana.
