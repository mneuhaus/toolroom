# Etappe 3 — Bericht für Marc und Fable

Stand 18.09.2026, nach dem Nachtlauf. Auftrag war `PLAN-etappe3.md`.
Kein Onshape-Aufruf, kein `python3`, kein Git. Alles offline auf STEP + `machine.json`.

## Testsummen (letzter tatsächlicher Lauf, nicht geschätzt)

```
uv run pytest tests -q                    (toolroom/pruefstand)
  243 passed, 4 warnings in 50.92s        vorher: 199 passed

uv run --project .../pruefstand pytest spec/test_tray_r1.py -q
  69 passed, 1 xfailed, 4 warnings in 56.41s    vorher: 62 passed, 1 xfailed
```

Nichts gelockert, nichts umgeschrieben, damit etwas grün wird. Der eine `xfailed` ist der
bekannte aus Etappe 2 (`T65`, Sägezahn 20°/4, 3,29 mm³ in die hintere Talwand) und
unverändert.

**Neue `xfail` gibt es keine.** Jede Messung in diesem Auftrag hat beim ersten oder zweiten
Anlauf einen Wert geliefert, der zur Erwartung passte — mit den unter „Entscheidungen"
genannten Ausnahmen, wo nicht die Toleranz, sondern die Erwartung im Plan an der Geometrie
vorbeiging. Diese Fälle sind mit dem gemessenen Wert im Test festgeschrieben, nicht
weggerechnet.

## Was fertig ist

### Aufgabe 1 — Fenster, die sich selbst messen

`Region.crop` setzt `meta['rand_schneidet_material']`; jedes Primitiv, das zuschneidet
(`gap`, `overlap`, `same_as`, `sweep`, `coverage`), kopiert das in
`result.fenster_schneidet_material` und in `as_dict()`. Terminalzeile bekommt ein `~`.

Messwerte am echten T60 (Zylinderfenster, Achse X durch Y 135 / Z 236):

| Fenster | gemessener max. Radius | `rand_schneidet_material` |
|---|---|---|
| r 4,5 × 6,0 ab X −103,5 (freier Zapfen) | 3,950 | False |
| r 4,5 × 12,0 ab X −104,3 (über den Bund) | 4,406 | True |

Das ist genau der Bund-Fall aus dem Plan: 4,41 statt 3,95, und der Messwert ist die
Fensterwand.

Dritter Zustand `None` = „es wurde nichts zugeschnitten, also gibt es dazu keine Aussage"
(kein `within`, oder der exakte Weg von `overlap`, der mit `region.solid()` schneidet statt
mit `crop`). Tests: `tests/test_fenster.py` (13), `test_tray_r1.py::
test_ein_fenster_ueber_dem_bund_misst_sich_selbst`.

### Aufgabe 2 — Interface

`src/pruefstand/interface.py`: `Interface`, `Match`, `InterfaceResult`, `interface_ok`,
`load_interfaces`, Schema `pruefstand.schnittstellen/1`. Vier Arten (pin/bore/seat/plane),
drei Ausgänge (UNIQUE / AMBIGUOUS / MISSING), die letzten beiden unentschieden (`U`).

Pflegedatei `rocking-photo-tray-r6d-tray-r1/spec/schnittstellen.yaml` mit drei echten
Schnittstellen. Gemessen im Referenzlauf:

| id | status | Messwerte |
|---|---|---|
| `journal_pin` | UNIQUE (1 Fläche) | r 3,950 · Achse 0,0° · Versatz 0,000 · gap zu H608 = 0,0000 |
| `horn_seat` | UNIQUE (4 Flächen) | r 6,900 · Achse 0,0° · gap zu HORN0 = 0,0159 |
| `hub_bolt_circle` | UNIQUE (4 Flächen) | r 1,310 · Teilkreis 9,5007 (soll 9,5) |
| Gegenfall `radius: 4.5` | MISSING | 0 Kandidaten |
| Gegenfall `radius: 4.5, tol 2` | AMBIGUOUS | 3 Kandidaten: r 3,00 / 3,95 / 5,25 |

Die vier Gegenfälle der Research als synthetische Tests in `tests/test_interface.py` (26
Tests). Ergebnis, Kriterium „nie falsches PASS" erfüllt:

| Defekt | Ausgang | Messwert |
|---|---|---|
| zu kleine Bohrung Ø2,4 statt Ø2,62 | UNIQUE, **FAIL** | `radius 1.2 statt 1.31 (0.110 > 0.05)` |
| viel zu kleine Bohrung Ø1,0 | MISSING, unentschieden | 0 Kandidaten |
| Achsversatz 0,15 mm | UNIQUE, **FAIL** | `offset 0.15 statt 0.0 (0.150 > 0.05)` |
| Achse 0,6° gekippt | UNIQUE, **FAIL** | `axis_deg 0.6 > 0.1` |
| Zwischenhindernis (0,3-mm-Hülse im Lager) | UNIQUE, **FAIL** | `gap 0.3000 zu L608 > 0.02` |
| fehlendes Mapping (`body` nicht gefunden) | unentschieden | — |
| Körper nur als Netz geladen | MISSING, unentschieden | — |

### Aufgabe 3 — `same_as(..., erwartet=[...])`

Punkte in einer erwarteten Region werden auf **beiden** Seiten verworfen,
`result.erwartet_ausgenommen` zählt sie. Referenz (T60 gegen die alte T01 aus dem
Maschinenmanifest, Ring r 12,6 × 6,0 um den Pivot):

```
ohne erwartet : max_deviation_mm = 3,6467   erwartet_ausgenommen = 0
mit  erwartet : max_deviation_mm = 0,0012   erwartet_ausgenommen = 180   (Pilot r 1,5)
```

Beide Zahlen stehen im Test. `diff_mm3` zählt den erwarteten Unterschied weiter mit — nur
das Urteil nimmt ihn heraus, sonst verschwände seine Größe aus dem Bericht.

### Aufgabe 4 — `urteil_auf` überall

`gap`, `sweep`, `access`, `coverage`, `protrusion` (beide Wege) setzen es jetzt; `overlap`
und `same_as` hatten es schon. Terminal: `[mesh]` / `[brep]` hinter jedem Messwert.
`test_schwenk_bleibt_frei` hat den Docstring-Absatz und die Assertion
`r.urteil_auf == 'mesh'`. Tabelle aller Primitive in `SPEC.md`.

### Zusatz 6 — Bericht angereichert

- `overlap` schreibt `contact_points` (Welt, mm, max. 64): im Netzweg die fcl-Kontaktorte,
  im exakten Weg der Schwerpunkt des Schnittkörpers je Paar. Leer, wenn der Kernwächter
  rechnet — der liefert nur eine Zahl zurück, und einen Ort zu erfinden wäre schlimmer.
  `pairs` stand schon im JSON.
- Jeder Testeintrag trägt `posen`, eine Liste von `State.as_dict()`. Beispiel aus dem
  Tray-Lauf: `test_schwenk_bleibt_frei[-135] → [{"hub": 0.0, "schwenk": -135.0}]`.

### Zusatz 7 + 8 — Doku und SPEC

- `docs/konzepte.md`: zwei neue Kapitel, „5. Fenster, die sich selbst messen" (mit dem
  Bund-Fall) und „6. Schnittstelle: benennen statt platzieren"; Folgekapitel umnummeriert,
  `Region.cylinder` in die Region-Tabelle nachgetragen.
- `docs/primitive.md`: Abschnitt `interface_ok` mit echtem Beispiel, `same_as`-Abschnitt um
  `erwartet` erweitert, `#in-arbeit` aufgeräumt (die sechs Primitive sind gebaut und
  exportiert, nur hier noch nicht beschrieben — das stand vorher falsch drin).
- `docs/README.md`: Stand, Etappe-3-Liste, drei Projektläufe, „nicht gebaut"-Absatz.
- `docs/fallstricke.md`: drei neue Einträge (Zylinderfenster über Rundteil, MISSING statt
  FAIL bei Interface, `erwartet` nimmt Punkte heraus und kein Volumen).
- `SPEC.md`: Verträge für `Region.cylinder` / `rand_schneidet_material`,
  `fenster_schneidet_material` (im Abschnitt „Nichts gemessen"), `urteil_auf` mit Tabelle
  je Primitiv, `same_as(erwartet=)`, `interface_ok`, ein eigener Abschnitt `Interface` mit
  YAML-Schema, `Match` und Suchfenster, sowie `posen` und `contact_points` beim Plugin.

## Entscheidungen zwischen zwei Lesarten

1. **Zylindermantel: Kreuzungstest statt `rand_unschaerfe_mm`.** Der Plan schreibt für den
   Mantel „innerhalb `rand_unschaerfe_mm`". Das ist `radius/8` = 0,5625 mm bei r 4,5. Der
   freie Zapfen endet 0,55 mm vor der Wand — mit diesem Maßstab wäre der Fall, den der Plan
   als **False** erwartet, als True gemeldet worden. Umgesetzt ist stattdessen: ein Dreieck
   mit Ecken beidseits des Radius wird von der Wand durchschnitten. Exakt, billiger, und es
   trennt beide Plan-Fälle sauber.
2. **Die Deckel eines Zylinderfensters zählen nicht mit.** Sonst wäre der Zapfenfall
   ebenfalls True (das Fenster X −103,5…−97,5 schneidet den Zapfen an beiden Enden ab). Der
   Befund geht nicht verloren: `meta['rand_deckel_schneidet_material']`.
3. **Bund-Fenster: Länge 12, nicht die im Plan genannte X-Spanne.** Der Plan sagt „r 4,5 ×
   12 … X −104,3…−93,2"; das sind 11,1 mm, nicht 12. Mit 11,1 misst man 4,275, mit 12,0
   misst man 4,406 — also die 4,41 aus dem Plan. Genommen: Länge 12,0.
4. **`fenster_schneidet_material` ist dreiwertig.** `None` heißt „nichts zugeschnitten,
   keine Aussage". Ein `False` dort, wo gar nicht zugeschnitten wurde (exakter
   `overlap`-Weg, `coverage` mit Punktregion, `protrusion`), wäre eine Behauptung über einen
   Rand, den niemand angesehen hat.
5. **`schnittstellen.yaml` hat eine Wurzelabbildung.** Der Plan zeigt eine blanke Liste,
   verlangt aber `schema: pruefstand.schnittstellen/1`. Beides geht nicht; gebaut ist
   `schema:` + `schnittstellen:` wie in `schrauben.yaml`.
6. **`horn_seat` mit gemessenen statt den Beispielzahlen.** Die YAML im Plan nennt
   `origin [93.3,135,236]`, `radius 12.0`, `inner_radius 9.5`. Dort steht die Außenwand der
   Nabe. Der SC09-Hornsitz ist die Kreuztasche X 109,6…112,15 mit vier Wänden r 6,9 um den
   Zentrierzapfen; HORN0 liegt bei X 109,9…114,0. Mit den Beispielzahlen liegt der Partner
   **außerhalb** des Fensters und die Prüfung endet „nichts gemessen". Gebaut ist die
   gemessene Geometrie, die Absicht des Plans bleibt erhalten: Ring, `count: 4`,
   Zentrierzapfen ausgenommen, Partner HORN0, Formschluss 0,0159 mm.
7. **Suchfenster weiter als Urteilstoleranz.** Wären beide gleich (wie die Plan-Formulierung
   nahelegt), könnte eine gefundene Fläche nie durchfallen — sie wäre ja mit genau der
   Urteilstoleranz gefunden worden, und `interface_ok` hätte außer dem Partnerspalt keinen
   FAIL-Pfad. Gesucht wird deshalb mit mindestens 0,25 mm / 1,0° / 0,25 mm. Folge, die man
   kennen muss: ein Maß, das weiter danebenliegt, endet als MISSING (unentschieden) statt
   als FAIL mit Messwert. Steht in `docs/fallstricke.md`.
8. **Gegenfall AMBIGUOUS hat drei Kandidaten, nicht zwei.** Der Plan sagt „(Bund und
   Zapfen)". Mit `radius 4.5, tolerance.radius 2` passt auch der Zentrierzapfen r 3,0
   (Abstand 1,5). Der Test schreibt `[3.0, 3.95, 5.25]` fest.
9. **`same_as`-Referenz misst 3,65 statt der im Plan genannten 3,94.** Die 3,94 stammen aus
   dem älteren Quaderfenster über der Stirnwand; der hier geforderte Ring r 12,6 um den
   Pivot liefert 3,6467. Der Test steht auf dem gemessenen Wert (3,65 ± 0,1), nicht auf dem
   erinnerten.
10. **Pose im Bericht: zwei Haken, und eine Liste.** Kleinster Eingriff wäre nur
    `State.apply()` gewesen — aber Szenen sind je Pose gecacht, beim zweiten Test mit
    derselben Pose läuft `apply` nicht mehr. Deshalb zusätzlich `_common.as_bodies()`, wo
    jedes Primitiv `Scene`/`at` auflöst. Und eine **Liste** statt eines Feldes, weil ein
    Test mehrere Posen durchfahren darf; ein einzelnes Feld müsste sich für eine
    entscheiden. Beschrieben in `SPEC.md`.

## Was ausdrücklich nicht gemacht wurde

- **Aufgabe 5** (fünfter Ausgang `UNSUPPORTED`, sechsteilige Toleranz-Taxonomie,
  Face-ID-Sidecar, konservative Rotationsschranke) — laut Auftrag nicht anzufassen. Der
  `face`-Schlüssel in `candidates` ist deshalb ein Flächenindex (`<body.key>#<i>`) und kein
  stabiler Identifier; er taugt zum Nachsehen im selben Lauf, nicht zum Vergleich über
  Revisionen. Steht so in `SPEC.md`.
- **Keine neuen Bilder** in `docs/bilder/`. Die beiden neuen Kapitel in `konzepte.md` haben
  keine Abbildung; die vorhandenen Skripte wurden nicht neu ausgeführt.
- **`sweep`, `access`, `screw_chain`, `print_pose`, `stability`, `relevance`** sind in
  `docs/primitive.md` weiterhin ohne Signatur und Beispiel. Sie bekommen nur `urteil_auf`
  (Aufgabe 4); ihre Doku-Abschnitte waren nicht Teil des Auftrags. Der irreführende Satz
  „in `__init__.py` noch nicht exportiert" ist korrigiert — exportiert sind sie längst.
- **Kein Umbau von `sweep` auf BRep**, wie im Plan ausdrücklich verlangt.
- **Kein erwartetes Volumen in `diff_mm3`.** `same_as(erwartet=...)` nimmt Abtastpunkte
  heraus, nicht das Differenzvolumen. Das Urteil ist sauber, der Nebenwert enthält den
  erwarteten Unterschied weiter — bewusst, damit seine Größe im Bericht steht.
- **Kein `interface_ok` im Hopperboden- und Riemenklemmen-Projekt.** Nur das Tray-Projekt
  war als Referenzfall genannt; die beiden anderen Specs sind unberührt.

## Wo Fable hinsehen sollte

`rocking-photo-tray-r6d-tray-r1/var/review/pruefstand.json`. Je Test stehen dort jetzt
`posen`, je Messwert `urteil_auf` und — wo zugeschnitten wurde —
`fenster_schneidet_material`. Auffällig und richtig: die beiden
Schnittstellentests mit Partner tragen `~`, weil H608 bzw. HORN0 aus dem
Schnittstellenfenster herausragen. Das ist der Hinweis, wie er gedacht ist: kein Fehler,
aber eine Stelle, an der man wissen will, warum.
