---
name: onshape-cad
description: "Onshape-Konstruktion und Überarbeitung: FeatureScript-Revisionen, Erhalt nativer Benutzer-Features, Adapter an bestehenden Schnittstellen, symmetrische Gleichteile, Geometrieprüfung und Assembly-Referenzen. Erfahrungen aus BeltFeeder, Sparky und Alternate Chute / SC15. Für Transport, Schreib-Timeouts und Metering zuerst onshape-bridge lesen."
---

# Onshape CAD — Konstruktion und Revisionen

Dieser Skill deckt das KONSTRUIEREN ab. Der Transport (Session-Bridge, keine
Direktcalls auf cad.onshape.com, Rate-Limit-Regeln, Mode A/B) steht im Skill
`onshape-bridge` — der gilt immer zuerst.

## Grundsatz: FeatureScript-first

Feature-Tree-Reads und FS-Eval haben knappe, getrennte Rate-Limit-Budgets.
Studio-Edits über die Session-Bridge verbrauchen nach bisheriger Messung kein
API-Key-Kontingent, unterliegen aber ebenfalls Rate-Limits. Ein an eine
Quell-Mikroversion gebundenes Custom Feature übernimmt Studio-Edits nicht
allein durch den Upload: seine Namespace-Referenz muss aktualisiert werden.
Details: [FS-Revisionen und lokale Dateien](references/revision-workflow.md).
Vor Änderungen an einem bestehenden Studio dessen aktuelle native Features
und Benutzeränderungen sichern. Ein alter Generator darf sie nicht ersetzen;
bei geeigneter Geometrie ein separates Finishing-Feature ergänzen. Bei Adaptern,
Flap-Varianten oder Gleichteilen zusätzlich
[Schnittstellen und Varianten](references/retrofit-and-variants.md) lesen.
Darum:

- Neue Geometrie als Custom Feature im zentralen Feature Studio bauen
  (ein `annotation { "Feature Type Name": … } defineFeature`-Block pro Feature),
  per Studio-Contents-POST editieren:
  `GET/POST /api/v9/featurestudios/d/{d}/w/{w}/e/{e}` (`BTFeatureStudioContents-2239`).
- Nur `op*`-Primitive nutzen (`opExtrude`, `opBoolean`, `opLoft`, `opSweep`,
  `opDeleteBodies`, `newSketchOnPlane`+`sk*`) — die High-Level-Wrapper
  (`extrude()` etc.) sind im defineFeature-Kontext nicht auffindbar.
- `defineFeature` braucht `precondition { }`; in preconditions ist nur `==`
  erlaubt (kein `>`); KEINE Umlaute in Annotation-Namen; `~` konvertiert zu
  String (`toString()` existiert nicht).

### FS-Chirurgie (Studio-Quelltext per Skript editieren)

- **Splices IMMER segment-lokal:** erst den Feature-Block isolieren
  (`i0 = src.index('"Feature Type Name" : "X"')`,
  `i1 = src.index('annotation { "Feature Type Name"', i0+10)`), dann nur in
  `src[i0:i1]` ersetzen. NIE global `src.index()`/`replace` — Muster wie
  `id + "u"` existieren mehrfach; ein globaler Treffer im falschen Feature
  dupliziert Code.
- Vor jedem POST: Klammerbilanz prüfen (`(){}[]` paarweise zählen) und
  Ersetzungs-Counts asserten (`assert seg.count(alt) == n`).
- **Parse-Error-Signatur:** ALLE Part Studios zeigen plötzlich 0 Teile
  → das Studio parst nicht mehr. Ursachen bisher: globaler Splice traf zweites
  Feature; Python-Escapes (`\\\"`) hinterließen Backslashes im FS.
- Insert-Snippets dürfen nur Variablen nutzen, die das ZIEL-Feature deklariert
  (Symptom sonst: Feature ERROR, Teil fällt auf Basis-Features zurück).
  Löschungen explizit per `opDeleteBodies` pro Block statt geteilter
  `sketches`-Variable.
- Zahlen in `plane()`-Normalen und `opExtrude`-Directions brauchen VOLLE
  Präzision (≥15 Stellen) — auf 4–6 Stellen gerundete Unit-Vektoren scheitern
  STILL (Sketch entsteht nicht, Cut trifft Luft).

## Geometrie-Patterns

- **Boolean-Lotterie:** tangentiale Anschlüsse (Boss an Rundung, Steg an
  Fläche, Rib an Bohrungswand) brauchen 0,2–0,5 mm ÜBERLAPPUNG, exakte Tangente
  = NON_MANIFOLD oder lose Bodies. Rib-Profile in frische Bohrungen: r+0,25
  in die Wand ankern.
- **Keine per-Kante-Fillet-Loops** über Union-Kanten — Regeneration hängt
  Minuten. Wenn ein lokaler Fallback einzelne Kanten überspringt, diese erfassen
  und das tatsächliche Kantenergebnis prüfen; `try silent` beweist keinen Erfolg.
  Kernel-Fillets scheitern oft zu Recht (Radius > geometrisch möglich) —
  Kehlen dann als analytische Tangentenbögen direkt ins Sketch-Profil rechnen.
- **Slab-Falle:** verschachtelte Rects in einem Sketch füllen die Region —
  Rahmen als 4 Streifen-Rects bauen; Löcher NICHT im Panel-Sketch, sondern
  als separate REMOVE-Extrudes nach dem Union.
- **Frustum/Konus-Cut:** `opLoft` mit
  `"profileSubqueries": [qSketchRegion(a,false), qSketchRegion(b,false)]`
  zwischen zwei Offset-Ebenen; Mündung 0,1 AUSSERHALB des Materials starten.
- **Rounded-Rect im FS:** 4 Linien + 4 `skArc`, Bogen-Mittelpunkt =
  Ecke + r/√2 auf der Diagonale.
- **Sketch-Basis explizit bestimmen:** lokale y-Achse = Normale × lokale
  x-Achse. Bei x=+X und Normale=+Y folgt y=−Z; mit Normale=−Y folgt y=+Z.
  Die beabsichtigte Seite aus dieser Basis ableiten, nicht aus einem pauschalen
  Front-/Back-Namen. Extrude-Richtung separat wählen, Einheitsvektoren prüfen.
- Nach topologieändernden Cuts/Unions Ziel-Queries neu auflösen und die erwartete
  Body-Anzahl prüfen. Auch eine zuvor robuste Query kann ungültig werden; Details
  und Diagnose stehen im Revisions-Workflow.
- **Konische Steckverbindungen (Lehre aus der Brace-Passung):** Nase und
  Tasche konisch aufeinander zulaufend macht self-aligning, aber das MASS
  definiert ein PLANER Tiefenanschlag (Spitzenfläche auf Taschenboden) —
  nie der Kegel selbst (Presssitz = toleranzabhängiges Maß). Der volle
  Querschnitt muss exakt an der Fügefläche enden: ragt er auch nur 0,6 mm
  weiter, gibt es eine sichtbare Stufe UND er klemmt im Konus.

## Montage vor Detailkonstruktion

Bei Adaptern und Mechanismen die [Montageprüfung](../cad-fdm-design/references/assembly-review.md)
anwenden: separate Vormontagen, tatsächliche Schraubenköpfe und Werkzeugwege,
Zusammenführen der Baugruppen und anschließend Betriebsbewegung prüfen.
Bei einer Platte mit entgegengesetzten Schraubrichtungen zuerst nach einer
zyklischen Montagereihenfolge suchen. Große Zugangsfenster dürfen die tragende
Wand nicht beiläufig entfernen; ein geteilter Adapter mit breiter Anlage und
zugänglicher Verbindung ist eine mögliche Lösung, keine Vorgabe für jedes Teil.

## Verifikations-Loop (passend zur Geometrieänderung)

1. **Teilezahl** (`GET /api/parts/...`): Soll-Anzahl? Mehr = Boolean still
   fehlgeschlagen (Tool-Reste als Mini-Bodies), weniger/0 = Parse-/Regen-Error.
2. **Bounding-Box** gegen Soll-Maße.
3. **Volumen-Delta** als Plausibilitätsprüfung: bei einem einzelnen erwarteten
   Cut kann unverändertes Volumen auf einen Leerschnitt hindeuten. Gleiches
   Gesamtvolumen beweist weder gleiche Form noch korrekte Passflächen; die
   betroffenen Konturen, Achsen und Kontakte zusätzlich messen.
4. **Renders** (`shadedviews`, eigenes Budget-Fenster): iso für Gesamtbild,
   **Silhouetten-Ansichten (top/front) für Passflächen** — eine Stufe zeigt
   sich als Kerbe im Umriss, ein sauberer Konus als glattes Trapez.
   `pixelSize:0` = auto-fit; feste pixelSize = m/px (0,0001 ≈ 0,1 mm/px).
5. Bewegliche Gruppen auch um neue Adapterhälften, Schrauben, Muttern und
   Scheiben erweitern. Kontaktfreigaben nach Funktion/Teileidentität formulieren,
   nicht nach alten Array-Indizes. Geänderte Halter und überstehende Schrauben
   über den betroffenen Hub gegen die vollständige Referenz prüfen. Nach rein
   lokalen Pfad-/Dokumentationsänderungen reichen entsprechende Offline-Checks.
6. Wenn Renders Teile „verlieren": erst hidden-Status im UI prüfen
   (hidden wirkt auf shadedviews), dann erst Fehler suchen.

## Assembly-Hygiene

- **partId-Wechsel:** Feature-Delete/-Insert und topologieändernde FS-Edits
  können die partId ändern. Onshape kann Assembly-Referenzen automatisch
  nachführen; beim Funnel Guide R4 geschah dies für alle sechs Instanzen.
  Nach der Änderung den Ist-Zustand auditieren und nur tatsächlich gebrochene
  Referenzen reparieren, nicht vorsorglich alle Instanzen löschen/einfügen.
  Mit `sorter-beltfeeder-handoff/scripts/asm_audit.py` als Muster jede
  Instanz-partId gegen den Ist-Zustand ihres Elements prüfen, über alle Assemblies
  des Dokuments. Ein Cleanup kann auch Instanzen in Neben-Assemblies betreffen.
- Baseline und Ergebnis getrennt halten: bestehende Legacy-Waisen dokumentieren,
  ohne sie als neuen Fehler zu zählen oder ungefragt andere Baugruppen zu ändern.
  Geänderte Körperidentität und veraltete Geometrie-Caches getrennt prüfen.
- **Posen deterministisch** aus Träger-Teil × bekannter Relativ-Pose rechnen
  (T_brace = T_plate ⊕ lokaler Offset), NIE relative Schübe mit heuristischer
  Instanz-Klassifikation.
- Instanz einfügen: `POST .../instances` → Instanz landet auf Identity →
  Diff der Instanzliste liefert die neue ID → `POST .../occurrencetransforms`.
  Für ASSEMBLY-Instanzen `isRelative:true` (false kollabiert Kinder);
  Der damals getestete Mate-Endpoint lieferte 404; dieser Workflow verwendete
  feste Posen. Solche Assemblies als positioniert kennzeichnen. Weder vollständige
  Instanzlisten noch eine Schwenkprobe belegen vorhandene Bewegungs-Mates oder
  kalibrierte Servo-Endwinkel.
- Instanz-Node-IDs werden von Onshape RECYCELT — gelöschte IDs nie
  hartkodiert wiederverwenden. Instanzen leerer/ERROR-Studios = sofortige
  Waisen. featureIds können `/` enthalten → URL-encoden.
- Standard-Content (DIN-Schrauben): configuration-String ist SIGNIERT —
  nie selbst bauen, nur von einer UI-inserierten Referenz-Instanz klonen.

## Design-Standards (Marc, verbindlich)

- **Formschluss vor Schrauben; keine Kerben** (0,42-Fasen / R4,2-Rundungen);
  Plastikschrauben liegend drucken.
- **M3-Crush-Grip** (kanonisch, `m3_hybrid_hole`): Wand r2,1, 3 Rippen als
  R0,84-Bögen tangential an r1,1 (lichtes Ø2,2), Übergänge R0,42.
  Nachrüst-Rezept: Ø6,3-Clean-Bore → frische Ø6,6-Scheibe (0,15 Anker) →
  ein Wellen-Kontur-Cut (12 Bögen). Durchgang = Ø3,4.
- **608-Lagersitz:** Tasche Ø22,7 + 6 Crush-Ribs r0,7 auf r11,6.
- **Wellen-Klemmung:** achsparallele M3 presst über Ø2,8-Kanal (0,2 Overlap
  zur Bohrungswand) die Flanke aufs D-Flat.
- **Rev-Gravursystem:** jedes Teil trägt „NAME Rn" (Höhe 2,4) auf VERDECKTER
  Fläche (Unterseite/Innenseite); zentrale REVS-Tabelle
  (`const REVS = {...}` im Feature Studio); bei jeder GEOMETRIE-Änderung
  bumpen, Kosmetik (Gravur-Position etc.) bumpt nicht.
- **Druckbarkeit vor Schönheit:** Teile müssen aufs 250×250-Bett, supportfrei
  gedacht (Wände ≥45°, kopfüber/liegend orientieren), nichts über die
  Druckebene hinaus.
- **Förderstrecken:** in Förderrichtung bergauf darf NICHTS die Gasse
  verengen (Verkant-Falle) — Dosierung über Tunnel-Sektion (geschlossener
  Kanal, Durchlass = Mitnehmerhöhe + Luft), nicht über Torwände.
- **Ein verbindliches Höhen-/Maßsystem** pro Projekt festschreiben (z. B.
  BeltFeeder: Gurt-OBERKANTE 51,93, Rails 45,93, Tunneldach 59,93,
  Plattenabstand verschraubt 100,8) und jedes Teil dagegen messen — Maße nie
  lokal „passend" wählen.
- **Lokale Koordinaten dokumentieren:** pro Teil festhalten, welche lokale
  Fläche in der Standard-Pose innen/außen bzw. oben/unten ist (BeltFeeder-
  Platte: lokal y=0 = AUSSEN, y=−8 = INNEN). Der halbe Ärger kommt aus
  falsch geratenen Seiten.

## Arbeitsweise

- Bei länger laufenden Projekten Quellen, aktive Skripte, Referenzen, Exporte,
  Ergebnisse, Arbeitsdaten und Archive trennen; siehe
  [Projektablage](../cad-fdm-design/references/project-layout.md). Bewährte
  Skripte nach `scripts/`, keine API-JSON-Sammlung im Projekt-Hauptordner.
- Pro Projekt den dokumentierten Handoff pflegen, etwa `docs/HANDOFF.md`:
  IDs, Maßsystem, Teilestatus, Quirks und offene Punkte. Vor Weiterarbeit lesen.
- Wenn der Nutzer lokale Bilder nicht sehen kann: einen überprüften,
  erreichbaren Review-Artefakt-Link liefern; Vorgehen und Postplan-Erfahrung
  in [CAD-Ansichten teilen](references/sharing-views.md).
- Marc reviewt per Screenshot: auf Reklamationen hin erst die URSACHE im
  Modell finden (messen, Silhouette rendern), dann fixen, dann mit Render
  am selben Blickwinkel gegenbeweisen.
