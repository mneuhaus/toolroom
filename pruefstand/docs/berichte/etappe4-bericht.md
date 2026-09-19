# Etappe 4 — Bericht für Marc und Fable

Stand 18.09.2026. Auftrag war `PLAN-etappe4.md`. Kein Onshape-Aufruf, kein `python3`,
kein Git, kein STEP-Export von T41. Alles offline auf STEP + `machine.json`.

## Testsummen (letzter tatsächlicher Lauf, nicht geschätzt)

```
uv run pytest tests -q                       (toolroom/pruefstand)
  283 passed, 4 warnings in 57.46s           vorher: 243 passed              exit 0

uv run --project .../pruefstand pytest spec/test_tray_r1.py -q
  73 passed, 1 xfailed, 1 warnung,
  4 warnings in 59.60s                       vorher: 69 passed, 1 xfailed    exit 0

uv run --project .../pruefstand pytest spec/test_hopper_floor.py -q
  27 passed, 2 xfailed, 3 warnung,
  4 warnings in 15.35s                       vorher: 23 passed, 2 xfailed    exit 0
```

Zur Sicherheit mitgelaufen, weil dieselbe Bibliothek: Riemenklemme R1 unverändert
`13 passed, 2 xfailed, 4 warnings in 4.40s`.

Die drei bekannten `xfailed` (Tray T65 Sägezahn 3,29 mm³, Hopperboden R6d-Lücke zweimal)
sind unverändert. **Neue `xfail` gibt es keine** — kein Messverfahren hat einen Wert
geliefert, der eine Toleranz gerissen hätte; die Stellen, an denen die Erwartung im Plan
nicht zur Geometrie passte, sind unter „Entscheidungen" aufgeführt und mit dem gemessenen
Wert im Test festgeschrieben.

Die vier neuen `warnung`-Zeilen sind das gewollte Ergebnis dieser Etappe: die Formregeln
melden, der Exit-Code bleibt 0, Marc entscheidet.

## Was fertig ist

### Aufgabe 1 — `form.py`, Kantenklassifikation

`src/pruefstand/form.py`, `kanten(body) -> list[Kante]` über
`TopExp.MapShapesAndAncestors_s(EDGE -> FACE)`. Je Kante: `index`, `typ`, `laenge_mm`,
`mitte` (Welt), `richtung`, `knick_deg`, `art`, `normalen`, `flaechen` (`<key>#i` wie bei
`interface_ok`), `flaechen_mm2`, `radius_mm` + `kreis_mitte` bei Kreisen, `geschlossen`,
`halbierende`.

Vier Arten statt zwei: **konvex**, **konkav**, **tangential** (Knick < 1°, Übergang auf
eine Rundung — dort gibt es keine Ecke) und **unentschieden**. Mesh-only liefert eine
leere Liste; die vier Regeln darauf geben `unentschieden` mit dem Grund „kein BRep".

Gemessen an der Wanne T01: **79 Kanten, 54 konvex, 11 konkav, 14 tangential, 0
unentschieden.** Das sind exakt Fables Zahlen (79 Kanten, 11 konkave Geraden). Am
Hopperboden T05: 132 Kanten, 110 konvex, 18 konkav, 4 tangential.

### Aufgabe 2 — `absatz(body)`

Kantenpaar konvex + konkav an derselben Fläche, parallel < 2°, exakter Kantenabstand
(`BRepExtrema`) 0,3–3 mm, Stufe schmaler als lang, beide Nachbarwände parallel < 2°.

| Prüfkörper | Ergebnis |
|---|---|
| zwei Quader, 1,5 mm versetzt vereinigt | **2** — einer je Seite, je 1,5 mm über 20,0 mm |
| bündig | 0 |
| 0,1 mm versetzt (Naht) | 0 |
| 5,0 mm versetzt (gewollte Stufe) | 0 |
| **Wanne T01** | **0** — wie im Plan erwartet |
| **Hopperboden T05** | **6** — Befund, siehe unten |

### Aufgabe 3 — `kerbe(body, kontext, at=None)`

Konkave Kanten mit Knick > 60°; Strahl (`BRepIntCurveSurface_Inter`) von der Kantenmitte
entlang **beider** Flächennormalen; trifft er den eigenen Körper in 0,2–2,5 mm, ist die
Stelle eng. Bündelung im 5-mm-Raster zu Zonen. Erklärt ist eine Zone, wenn in 2,5 mm ein
Kontextkörper (Scene, Liste von Szenen = alle Posen, oder Bodies) oder eine Schraube aus
`schrauben.yaml` liegt, oder wenn sie in `spec/form.yaml` unter `erklaert:` steht.
Urteil auf `brep` (der BRep-Weg trägt; der Mesh-Weg wurde nicht gebraucht).

| Prüfkörper | Ergebnis |
|---|---|
| Klotz mit 1,0-mm-Schlitz | 2 Zonen, Spalt 1,000 mm, beide unerklärt |
| derselbe, mit 0,9-mm-Feder im Schlitz | 2 Zonen, **0 unerklärt** (Partner `F`) |
| derselbe, Zone in `form.yaml` erklärt | 2 Zonen, 0 unerklärt („erklärt: Kabelschlitz") |
| derselbe, Fremdkörper 40 mm weg | 2 Zonen unerklärt, `partner_mm` 27,5 mm |
| 4,0-mm-Schlitz | 0 Zonen — das ist ein Durchgang, keine Kerbe |
| **Wanne T01** (drei Schwenkposen −135/0/+45, 7 Schrauben) | **0 Zonen, 0 unerklärt, 0 mm enge Kanten** |
| **Hopperboden T05** (Maschinenszene) | 2 Zonen, **0 unerklärt** |

### Aufgabe 4 — `unverrundet(body, pose=None)`

Konvexe Kanten 80–100°, länger als 5 mm, die Außenkanten sind (Strahl entlang der
Winkelhalbierenden trifft den eigenen Körper nicht). Bohrungsmündungen und die Bettseite
einer Druckpose fallen heraus.

| Prüfkörper | Ergebnis |
|---|---|
| Quader 20³ scharf | 12, zusammen 240,0 mm |
| derselbe mit R4,2 verrundet | 0 |
| Quader 4³ | 0 (Kanten zu kurz) |
| Klotz mit Ø8-Loch | 12 — der Lochrand zählt nicht mit |
| Topf (offene Tasche) | 16 — die vier Kanten am Taschenboden (z −5) fehlen zu Recht |
| Quader auf dem Bett, `pose` gesetzt | 12 → **8** (die vier Bettkanten fallen heraus) |
| **Wanne T01** | **16**, zusammen **1694,18 mm** |
| **Hopperboden T05** | 32, zusammen 1159,39 mm |

### Aufgabe 5 — `splitter(body)`

Kanten < 0,42 mm; Flächen < 1 mm² mit einem Nachbarn > 100 mm²; Nachbarflächen mit Knick
< 0,5°, die trotzdem durch eine Kante getrennt sind.

| Prüfkörper | kurze Kanten / winzige Flächen / unverschmolzen |
|---|---|
| Quader 20×20×10 | 0 / 0 / 0 |
| 0,3 mm versetzte Quader | **4** / 0 / 0 (die Stirnkanten der Stufe) |
| 0,04 mm versetzte Quader | 4 / **2** (je 0,80 mm² an 200-mm²-Wänden) / 0 |
| Zylinder | 0 / 0 / **0** — die Naht zählt nicht (Regression, siehe Entscheidung 3) |
| **Wanne T01** | **0 / 0 / 0** — wie im Plan erwartet |
| **Hopperboden T05** | 34 / 16 / 0 |

### Aufgabe 6 — Prüfbudget und `status: not_built_yet`

Jeder Testeintrag in `var/review/pruefstand.json` trägt jetzt

```json
"budget": {
  "geprueft":      [{"primitiv": "absatz", "koerper_n": 1, "koerper": ["T05"],
                     "urteil_auf": "brep"}],
  "uebersprungen": [{"was": "brep", "anzahl": 102, "keys": ["C00", "..."]}],
  "angenommen":    [{"primitiv": "absatz", "regel": "absatz",
                     "versatz_mm": [0.3, 3.0], "parallel_deg": 2.0, "kanten": 132}],
  "koerper":       {"T05": true}
}
```

Kleinster Eingriff wie verlangt: `Result._publish()` bucht selbst; die Körper kommen aus
`_common.as_bodies()` (der einzige Ort, an dem alle Primitive ihre Körper durchreichen)
über `results.merke_koerper` / `zieh_koerper`. Primitive ergänzen `result.uebersprungen`
und `result.annahmen`. Im Kopf des Berichts und als letzte Terminalzeile steht die Summe
des Laufs:

```
Prüfstand    Budget: 191 Messungen an 132 Körpern (102 davon nur Netz), 233 übersprungen, 150 Annahmen
Tray         Budget: 210 Messungen an 117 Körpern (102 davon nur Netz), 4751 übersprungen, 219 Annahmen
Hopperboden  Budget:  32 Messungen an 102 Körpern (102 davon nur Netz), 344 übersprungen,  54 Annahmen
```

`status: not_built_yet` ist in `schrauben.yaml`, `schnittstellen.yaml` und `montage.yaml`
erlaubt (und nur dieser Wert, sonst fliegt der Lader). `interface_ok`, `screw_chain` und
`access` kehren damit sofort über `results.ohne_urteil(...)` zurück und sind
**unentschieden**; für einen Montageschritt sagt es `Step.nicht_gebaut`.

### Aufgabe 7 — Doku und SPEC

- `docs/konzepte.md`: neues Kapitel **7. Form: die Stilregeln messen** mit Marcs Bild
  `bilder/t41-absaetze-marc-2026-09-17.png` und der Vergleichstabelle Wanne/Hopperboden;
  neues Kapitel **11. Prüfbudget**; Folgekapitel umnummeriert (7→8, 8→9, 9→10).
- `docs/primitive.md`: Abschnitt „Form: absatz, kerbe, unverrundet, splitter" mit
  Signaturen, Rückgabetabelle und echtem Beispiel am Hopperboden; Inhaltsverzeichnis.
- `docs/fallstricke.md`: neuer Abschnitt „Form messen" mit vier Einträgen (Schwerpunkt-
  Sonde, Zylindernaht, R4,2 an Bohrungen, Budget je Messung).
- `docs/README.md`: Etappe-4-Liste, neue Projektsummen.
- `SPEC.md`: Verträge für `kanten`, `absatz`, `kerbe`, `unverrundet`, `splitter`,
  `spec/form.yaml`, Prüfbudget und `status: not_built_yet`; Paketliste und
  Plugin-Abschnitt nachgezogen.

Alle Zahlen in diesen Texten stammen aus den oben genannten Läufen.

## Befunde

### Wanne T01 — die 16 unverrundeten Außenkanten

Alle 16 sind gerade Linien mit exakt 90° Knick. `nach außen` ist die Winkelhalbierende,
also die Richtung, in die eine Rundung Material wegnehmen würde.

| # | Länge mm | Mitte (Welt) | nach außen | was das ist |
|---|---|---|---|---|
| 1 | 186,40 | (0, 65,0, 262,0) | (0, −0,71, +0,71) | oberer Wannenrand vorn, außen |
| 2 | 186,40 | (0, 205,0, 262,0) | (0, +0,71, +0,71) | oberer Wannenrand hinten, außen |
| 3 | 180,10 | (0, 68,15, 262,0) | (0, +0,71, +0,71) | oberer Wannenrand vorn, innen |
| 4 | 180,10 | (0, 201,85, 262,0) | (0, −0,71, +0,71) | oberer Wannenrand hinten, innen |
| 5 | 140,00 | (−93,2, 135,0, 262,0) | (−0,71, 0, +0,71) | Stirnwand links, Oberkante außen |
| 6 | 140,00 | (+93,2, 135,0, 262,0) | (+0,71, 0, +0,71) | Stirnwand rechts, Oberkante außen |
| 7 | 133,70 | (−90,05, 135,0, 262,0) | (+0,71, 0, +0,71) | Stirnwand links, Oberkante innen |
| 8 | 133,70 | (+90,05, 135,0, 262,0) | (−0,71, 0, +0,71) | Stirnwand rechts, Oberkante innen |
| 9 | 85,45 | (−93,2, 100,0, 219,5) | (−0,71, −0,41, −0,58) | Stirnwand links, vordere Schrägkante |
| 10 | 85,45 | (−93,2, 170,0, 219,5) | (−0,71, +0,41, −0,58) | Stirnwand links, hintere Schrägkante |
| 11 | 85,45 | (+93,2, 100,0, 219,5) | (+0,71, −0,41, −0,58) | Stirnwand rechts, vordere Schrägkante |
| 12 | 85,45 | (+93,2, 170,0, 219,5) | (+0,71, +0,41, −0,58) | Stirnwand rechts, hintere Schrägkante |
| 13 | 18,00 | (−93,2, 65,0, 253,0) | (−0,71, −0,71, 0) | Stirnwand links, vordere Senkrechte |
| 14 | 18,00 | (−93,2, 205,0, 253,0) | (−0,71, +0,71, 0) | Stirnwand links, hintere Senkrechte |
| 15 | 18,00 | (+93,2, 65,0, 253,0) | (+0,71, −0,71, 0) | Stirnwand rechts, vordere Senkrechte |
| 16 | 18,00 | (+93,2, 205,0, 253,0) | (+0,71, +0,71, 0) | Stirnwand rechts, hintere Senkrechte |

Summe 1694,18 mm. Meine Einschätzung, damit Marc nicht bei null anfängt: die acht Kanten
des oberen Randes (1–8) sind der Griffbereich — dort würde ich R4,2 erwarten, oder
wenigstens einen Kantenbruch. Die vier Schrägkanten (9–12) und die vier Senkrechten
(13–16) sind die Silhouette der Stirnwände; dort ist „gewollt scharf" plausibel, weil die
Wand nur 18 mm hoch ist und R4,2 fast die halbe Höhe fräßte. **Das ist ein echter
Befund, kein Fehler der Regel** — die Kanten sind alle wirklich frei zugänglich und
wirklich unverrundet.

Nicht darunter, und das ist die Lesart-Entscheidung Nr. 2: sieben Bohrungsmündungen
(r 1,70 viermal, r 3,10, r 6,10 zweimal). Sie erfüllen jedes Merkmal der Regel außer dem
Sinn: in ein Ø3,4-Loch passt kein R4,2.

### Hopperboden T05 — sechs Absätze

| Versatz mm | Länge mm | Ort (Welt) | Flächen |
|---|---|---|---|
| 0,3332 | 26,658 | (−101,43, −13,13, 208,00) | T05#5 / T05#7 / T05#8 |
| 0,3332 | 26,658 | (+101,43, −13,13, 208,00) | T05#12 / T05#19 / T05#18 |
| 0,3208 | 2,510 | (−112,25, −30,30, 210,95) | T05#32 / T05#36 / T05#37 |
| 0,3540 | 2,510 | (−112,42, −30,46, 210,73) | T05#35 / T05#37 / T05#36 |
| 0,3208 | 2,510 | (+112,25, −30,30, 210,95) | T05#40 / T05#43 / T05#44 |
| 0,3540 | 2,510 | (+112,42, −30,46, 210,73) | T05#42 / T05#44 / T05#43 |

Alle sechs liegen paarweise gespiegelt und alle knapp über der unteren Grenze von 0,3 mm.
Das ist nach meiner Analyse ein **echter Befund** und genau Marcs Bild in klein: an der
Kante der Auflagerippe (|X| 101,4) und an den Wagenecken (|X| 112,2–112,4) läuft die
Kontur nicht durch, sondern springt um ein Drittel Millimeter. Drucktechnisch ist das
weniger als eine Bahnbreite — der Absatz wird also gar nicht gedruckt, er steht nur im
Modell und erzeugt dort zusätzliche Flächen.

### Hopperboden T05 — 32 unverrundete Außenkanten

Zusammen 1159,39 mm. Die vier längsten sind die Bodenkanten: 224,20 mm bei
(0, −6,94, 201,83) mit 83° Knick, 180,99 mm bei (0, −5,24, 205,49) mit 97°, sowie je
zweimal 91,95 mm und 90,66 mm bei |X| 124,6. Der Rest sind die Stufen an den
Wagenausschnitten (6 bis 27 mm). Echter Befund; ob R4,2 an einem Boden, der im Rahmen
sitzt, sinnvoll ist, entscheidet Marc.

### Hopperboden T05 — 34 kurze Kanten, 16 winzige Flächen

Kantenlängen: 0,0179 mm (8×), 0,0252 (2×), 0,0431 (8×), 0,1275 (2×), 0,1391 (2×),
0,1460 (4×), 0,1643 (2×), 0,3373 (2×), 0,3540 (4×). Flächen: 0,2989 mm² (2×), 0,3024 (2×),
0,4765 (2×), 0,5259 (2×), 0,6237 (2×), 0,7096 (2×), 0,8887 (2×), 0,9805 (2×). Die
kleinste Fläche klebt an einer 902,52 mm² großen Ebene; zwei weitere an einer von
28381,42 mm². Alle sitzen bei |X| 90,5 bis 112,6, also in denselben beiden Zonen wie die
Absätze. Echter Befund, dieselbe Ursache.

### Hopperboden T05 — zwei enge Stellen, beide erklärt

0,2812 mm Spalt über je 6,51 mm bei (±112,16, −30,52, 211,17); nächster Fremdkörper T41R
bzw. T41L in 0,478 mm. Das ist die Fuge zum Rahmen — **kein Befund**, und ein guter Beleg
dafür, dass die Ankerregel greift: ohne Kontext wären beide Zonen unerklärt gemeldet
worden.

## Entscheidungen zwischen zwei Lesarten

1. **Konvexität lokal statt über den Flächenschwerpunkt.** Der Plan nennt Fables Sonde als
   Vorlage: Schwerpunkt der zweiten Fläche relativ zur ersten Normalen. Gebaut ist die
   lokale Fassung — Richtung von der Kante *in die Nachbarfläche hinein*
   (`n2 × t`, Vorzeichen per Probepunkt auf der Fläche). Grund: an T05 kippen sechs
   Kanten (0,02 bis 0,57 mm lang, an einer 902 mm² großen Ebene) zwischen beiden
   Verfahren; der Schwerpunkt liegt dort 60 mm weit weg und sagt nichts über die Seite,
   auf der die Fläche an dieser Kante liegt. **An der Wanne sind beide Verfahren an allen
   79 Kanten einig** — Fables Zahlen bleiben also unverändert reproduziert.
2. **Bohrungsmündungen sind keine Außenkanten.** Der Plan definiert die Außenkante allein
   über den Strahl nach außen. Damit misst man an der Wanne **23** statt der im Plan
   genannten 16. Die Differenz sind genau sieben Kreiskanten an Bohrungsmündungen
   (r 1,70 ×4, r 3,10, r 6,10 ×2). Zusätzliches Kriterium: liegt der Krümmungsmittelpunkt
   eines Kreises nicht im Material, ist die Kante der Rand eines Lochs. Damit sind es 16,
   und die Regel behält ihren Sinn (R4,2 passt in kein Ø3,4-Loch).
3. **Die Naht eines Zylinders ist nicht „unverschmolzen".** Erste Fassung von `splitter`
   meldete an der Wanne **14** unverschmolzene Kanten — alle mit demselben Flächenindex
   zweimal (`T01#13 / T01#13`). Das sind Parameter-Nähte von Zylinderflächen, keine zwei
   Flächen. Die Regel verlangt jetzt zwei *verschiedene* Flächen; damit steht die Wanne
   auf 0/0/0 wie im Plan erwartet, und der synthetische Zylindertest hält das fest.
4. **`absatz` verlangt die gemeinsame Stufenfläche, nicht nur Nähe.** Ein Kantenpaar, das
   zufällig 1 mm auseinanderliegt, aber zu verschiedenen Taschen gehört, ist kein Absatz.
   Die Bedingung „beide Kanten liegen an derselben Fläche" macht das Verfahren gleichzeitig
   billig (kein N²-Abstandsvergleich über alle Kanten) und wörtlich: die Stufe *ist* diese
   Fläche.
5. **Der Kantenabstand kommt aus `BRepExtrema`, nicht aus den Mittelpunkten.** Bei zwei
   verschieden langen parallelen Kanten (Stufe endet früher als die Wand) läge der
   Mittelpunktabstand schief. Gemessen wird der echte kleinste Abstand der beiden Kurven.
6. **Vierte Kantenart `tangential`.** Der Plan nennt konvex und konkav. Eine verrundete
   Kante hat aber zwei Übergänge mit Knick 0°, und für die ist beides falsch. Sie bekommen
   `tangential` und fallen aus allen vier Regeln heraus — außer aus `splitter`, wo genau
   sie den unverschmolzenen Nachbarn ausmachen. Nebeneffekt: an der Wanne sind 14 der 25
   „konkaven" Kanten der Schwerpunktsonde in Wahrheit tangential; die 11 echten konkaven
   Geraden sind genau Fables 11.
7. **`kerbe` misst entlang beider Flächennormalen, nicht entlang einer.** Der Plan sagt
   „entlang der Flächennormale". Eine konkave Kante hat zwei, und welche auf die Gegenwand
   zeigt, hängt davon ab, wie der Schlitz liegt. Genommen wird der kleinere der beiden
   Treffer. Am synthetischen 1-mm-Schlitz liefert das exakt 1,000 mm.
8. **Ohne Kontext ist eine Zone nicht „unerklärt", sondern ungeprüft.** `kerbe` ohne
   Kontextkörper schreibt einen `uebersprungen`-Eintrag ins Budget (`was: kontext`). Die
   Zonen stehen trotzdem als unerklärt in der Liste — aber der Bericht sagt daneben, dass
   niemand nach einem Partner gesucht hat.
9. **Budget: Körper ohne BRep einmal je Test, nicht je Messung.** Wörtlich umgesetzt
   („was sie ausgelassen haben") hätte der Tray-Bericht 4749 gleichlautende Einträge und
   3,0 MB. Jetzt steht eine Sammelzeile je Test (`{was: brep, anzahl: 102, keys: [...]}`)
   und die vollständige Körperliste unter `budget.koerper`; der Bericht ist 0,5 MB groß.
   Die Zahl im Kopf des Laufs bleibt dieselbe, weil `anzahl` mitgezählt wird.
10. **Die Körperliste eines einzelnen Messeintrags ist bei 12 Namen gekappt**
    (`koerper_n` nennt die volle Zahl). Ein Sweep gegen die ganze Maschine fasst über
    hundert Körper an; sie bei jeder einzelnen Messung auszuschreiben macht den Bericht
    unlesbar. Vollständig steht die Liste je Test unter `budget.koerper`.
11. **`uebersprungen` und `annahmen` sind Eigenschaften, keine Klassenattribute.** Eine
    Liste an der Basisklasse `Result` teilten sich alle Ergebnisse — der erste
    übersprungene Körper stünde im Budget jeder späteren Messung. Sie werden je Instanz
    beim ersten Zugriff angelegt.
12. **Der Hopperboden-Lauf meldet „102 von 102 Körpern nur Netz", obwohl T05 ein BRep
    hat.** Das ist richtig und trotzdem erklärungsbedürftig: der Schlüssel `T05` wird in
    diesem Projekt für zwei Körper benutzt — das neue Teil aus dem STEP und den Vorgänger
    aus dem Maschinenkontext, der nur als STL vorliegt. Bei gleichem Schlüssel gewinnt im
    Budget die pessimistische Aussage. Wer das trennen will, muss den Vorgänger anders
    benennen; das war nicht Teil dieses Auftrags.

## Was ausdrücklich nicht gemacht wurde

- **Kein Mesh-Splitter-Test.** Laut Plan sinnlos (über die Hälfte aller Dreiecke einer
  Tessellierung sind Winzlinge). `splitter` verweigert deshalb auf Mesh-Körpern die
  Aussage, statt eine Zahl zu liefern.
- **Kein STEP-Export von T41**, kein Onshape-Aufruf. T41L/R bleiben Netzkörper; die vier
  Formregeln liefern daran `unentschieden` mit dem Grund „kein BRep". Fables
  Erwartungsbild an T41L (544 mm enge Kanten, unerklärt 0,95 mm bei Y 135/155 und 0,29 mm
  bei Z 265) ist damit in dieser Etappe **nicht** nachgemessen worden — das braucht einen
  BRep-Export und ist der nächste offene Punkt zu `kerbe`.
- **Kein Mesh-Weg in `kerbe`.** Der Plan lässt ihn als Alternative zu (`urteil_auf='mesh'`).
  Beide Referenzteile haben ein BRep; ein zweiter, ungetesteter Pfad wäre toter Code.
- **Keine Ästhetik-Heuristik** jenseits der fünf Regeln, kein `UNSUPPORTED`, keine
  Toleranz-Taxonomie.
- **Keine neuen Bilder** in `docs/bilder/`. Das Formkapitel zeigt Marcs Foto; die
  vorhandenen Skripte wurden nicht neu ausgeführt.
- **Kein `form.yaml` in den Projekten.** Weder Wanne noch Hopperboden brauchen eine
  erklärte Zone (die zwei Zonen von T05 erklärt der Rahmen selbst). Die Datei ist
  optional, das Schema ist gebaut und im Prüfstand getestet.
- **Kein Budget-Nachrüsten in den Primitiven.** Die `angenommen`-Einträge über
  `urteil_auf` hinaus gibt es bei den vier Formregeln (Grenzwerte, Raster, Kantenzahl).
  `coverage`, `sweep`, `screw_chain` und `print_pose` könnten ihre Abtastdichten
  nachtragen; sie liefern heute nur `urteil_auf` und, wo zutreffend,
  `fenster_schneidet_material`.

## Wo Fable hinsehen sollte

- `rocking-photo-tray-r6d-tray-r1/var/review/pruefstand.json`, Test
  `test_die_wanne_hat_keine_scharfen_aussenkanten`: der `warnung`-Eintrag mit allen 16
  Kanten unter `messwerte[0].kanten`.
- `rocking-photo-tray-r6d-hopper-floor-r1/var/review/pruefstand.json`, die drei
  `warnung`-Einträge (Absätze, scharfe Kanten, Splitter) und daneben
  `test_der_boden_hat_keine_unerklaerten_kerben`, der zeigt, wie eine enge Stelle durch
  einen Nachbarn erklärt wird.
- In beiden Dateien der Schlüssel `budget` je Test und in der Wurzel.
