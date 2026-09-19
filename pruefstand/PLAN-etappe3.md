# Prüfstand — Etappe 3: Schnittstellen als Objekte

Stand 17.09.2026, abends. Auftrag für einen Opus-Subagenten; Fable nimmt ab (liest Messwerte,
nicht nur Testfarben). Vorher lesen: `HANDOFF.md`, `SPEC.md` (Abschnitt „Primitive und
Ergebnisse"), `docs/fallstricke.md`, und als Referenzfall
`step-feeder/rocking-photo-tray-r6d-tray-r1/spec/test_tray_r1.py` (62 passed, 1 xfailed — muss so bleiben).

## Regeln, die weiter gelten

- **Kein Onshape-Aufruf.** Alles aus STEP + `machine.json`. Keine MCP-Werkzeuge von Onshape.
- `python3` ist gesperrt: immer `uv run python`, `uv run pytest` (Projektwurzel `toolroom/pruefstand`).
- Tests sind pytest. **Toleranzen nie lockern, damit etwas grün wird** — Messwert melden, `xfail(strict=True)`.
- „Nichts gemessen" macht rot. Jedes neue Ergebnisfeld läuft über `results` in den Bericht.
- Kein Git im cad-Workspace; keine `_v2`-Dateien.

## Warum diese Etappe

Zwei Referenzteile, vier Werkzeugfehler, und der häufigste Fehler war jedes Mal derselbe:
**ein von Hand gesetztes Messfenster, das sich selbst misst.** Box über der Auflage (Hopperboden),
Box über Stirnwandmaterial (3,94 mm „Abweichung"), Zylinder r=4,5 über dem Bund Ø10,5 (liefert 4,41
statt 3,95 — den Fensterradius). Die Research (docs/research-2026-09-17) nennt als Antwort
semantische Schnittstellen als First-Class-Objekte. Das bauen wir jetzt — und nur das, was die
beiden Referenzteile tatsächlich brauchen.

## Aufgaben

### 1. `Region`: Fenster müssen sagen, ob sie Material schneiden

`Region.crop()` (box und cylinder) setzt `region.meta['rand_schneidet_material'] = True`, wenn
das beschnittene Netz eine Fensterwand berührt (Punkte auf der Wand mit Toleranz 1e-6, beim
Zylindermantel innerhalb `rand_unschaerfe_mm`). Jedes Primitiv, das ein `Region` nimmt, kopiert das
in `result.fenster_schneidet_material` und in `as_dict()`. **Kein Urteil**, nur Hinweis; die
Zeile im Terminalbericht bekommt ein `~`. Test: Bund-Fall (Zylinder r=4,5 × 12 über
`T60`, X −104,3…−93,2 → True; über den freien Zapfen X −103,5…−97,5 → False).
In `SPEC.md` unter „Nichts gemessen" ergänzen: *„Ein Fenster, das Material schneidet, sagt das."*

### 2. `Interface`: Schnittstellen benennen statt Fenster platzieren

Neues Modul `src/pruefstand/interface.py`, Pflegedatei `spec/schnittstellen.yaml`
(`schema: pruefstand.schnittstellen/1`). Vier Arten reichen für beide Referenzteile:

```yaml
- id: journal_pin          # Lagerzapfen im 608
  kind: pin                # pin | bore | seat | plane
  body: T60                # Suchbegriff wie bei Parts.find
  frame: world
  axis: [1, 0, 0]
  origin: [-104.3, 135, 236]
  radius: 3.95
  length: 7.4              # nur der freie Zapfen, nicht der Bund
  partner: H608            # Maschinenkörper, optional
  tolerance: {radius: 0.05, axis_deg: 0.1, offset: 0.05}
- id: horn_seat
  kind: seat
  body: T61
  axis: [1, 0, 0]
  origin: [93.3, 135, 236]
  radius: 12.0
  inner_radius: 9.5        # Ring: Zentrierzapfen in der Mitte gehört nicht dazu
  length: 3.0
  partner: HORN0
```

`Interface.region()` liefert das passende `Region` (pin/bore/seat → `Region.cylinder`, plane →
`Region.box`). `Interface.match(body) -> Match` sucht im **BRep** die tragende Fläche
(Zylinderflächen nach Radius, Achsrichtung und Lage; Ebenen nach Normale und Abstand) und liefert
`status ∈ {UNIQUE, AMBIGUOUS, MISSING}` plus `candidates` (Fläche, gemessener Radius, Achsabweichung,
Versatz). **Nie stillschweigend den besten Kandidaten nehmen** (Research-Befund 6): AMBIGUOUS und
MISSING sind eigene Ergebnisse, im Plugin `U` wie „unentschieden".

`interface_ok(iface, parts, at=None) -> InterfaceResult`: Match + gemessener Radius/Achse/Versatz
gegen `tolerance`; `urteil_auf='brep'`. Wenn `partner` gesetzt: zusätzlich `gap` gegen den
Maschinenkörper im Fenster (Formschluss = 0,0 ± 0,02).

Referenztests in `test_tray_r1.py`: `journal_pin` (r=3,95, UNIQUE), `horn_seat` (Ring), 
`hub_bolt_circle` (vier Bohrungen Ø2,62 auf r=9,5 — als `bore` mit `count: 4`, jede UNIQUE) und
ein **Gegenfall**: `radius: 4.5` für den Zapfen → MISSING, `tolerance.radius: 2` → AMBIGUOUS
(Bund und Zapfen). Die vier Gegenfälle aus der Research (zu kleine Bohrung, Achsversatz,
Zwischenhindernis, fehlendes Mapping) als synthetische Tests in `tests/test_interface.py`;
Kriterium: jeder Defekt wird FAIL oder unentschieden, **nie** grün.

### 3. `same_as` mit erwarteten Unterschieden

`same_as(part, predecessor, region, erwartet: list[Region] = ())`. Punkte in einer erwarteten
Region zählen nicht; `result.erwartet_ausgenommen` = Anzahl. Referenz: `T60` gegen alte `T01` im
Ring r 12,6 um den Pivot, erwartet = Pilotbohrung (Zylinder r 1,5 auf der Achse) →
`max_deviation_mm < 0,05`. Ohne `erwartet` bleiben es 3,94 mm — der Test schreibt beide Werte hin.

### 4. `urteil_auf` überall, wo es fehlt

`gap`, `sweep`, `access`, `coverage`, `protrusion` (Mesh-Pfad) setzen `urteil_auf`. Im
Terminalbericht steht hinter dem Messwert `[mesh]` bzw. `[brep]`. `test_schwenk_bleibt_frei` im
Tray-Projekt bekommt einen Docstring-Satz und eine Assertion `r.urteil_auf == 'mesh'` — damit
sichtbar ist, dass „Schwenk frei" ein Mesh-Urteil ist (Research-Befund 5). Kein Umbau auf BRep.

### 5. Ausdrücklich **nicht** in dieser Etappe

Fünfter Zustand UNSUPPORTED, sechsteilige Toleranz-Taxonomie, Face-ID-Sidecar, konservative
Rotationsschranke. Begründung steht in der Memory `pruefstand-stand`: bisher hatte jede
Entscheidung klare Kanten; gebaut wird, sobald der zweite Fall wie „0,321 mm" auftaucht.

## Abnahme (Fable)

- `uv run pytest` in `toolroom/pruefstand`: bisher 199 passed, plus die neuen.
- `test_tray_r1.py`: 62 passed + 1 xfailed **plus** die Schnittstellentests; nichts gelockert.
- Fable liest `var/review/pruefstand.json` der Tray-Läufe: Radien, Achsabweichungen,
  `fenster_schneidet_material` je Test, `urteil_auf` je Messwert.
- `docs/primitive.md` und `docs/konzepte.md` um `Interface` und die Fenster-Regel ergänzt
  (im Stil der bestehenden Kapitel, mit dem Bund-Fall als Beispiel).
