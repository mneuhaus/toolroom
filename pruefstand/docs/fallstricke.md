# Fallstricke

Gesammelt aus `HANDOFF.md`, den Kommentaren im Quellcode, den beiden Referenzprojekten und
aus dem Bau dieser Doku. Jeder Punkt hat mindestens einmal Zeit gekostet.

## Einrichtung

**`ocp-gordon` muss auf 0.2.0 bleiben.** Neuere Versionen brechen `OCP.collections`, und
damit lädt build123d nicht mehr. Die Fassung steht in `pyproject.toml` fest verdrahtet
(`build123d==0.10.0`, `ocp-gordon==0.2.0`, Python 3.13). Nicht auf gut Glück hochziehen.

**`python3` ist im Shell-Profil umgebogen.** Jeder Aufruf geht über `uv run python …` oder
`uv run pytest …`, sonst bekommt man ein anderes Interpreter-Environment oder eine
Fehlermeldung statt eines Ergebnisses.

**Onshape wird nicht angefasst.** `GET features` und FeatureScript-Eval haben ein Budget
von 100 Aufrufen am Tag. Der Prüfstand arbeitet ausschließlich auf STEP- und STL-Dateien;
`machine.json` wird einmal je Maschinenrevision gebaut, nicht je Testlauf.

## Messen

**`overlap` liefert kein Volumen, wenn eine Seite nur ein Netz ist.** Exakt gerechnet wird
nur, wenn **alle** beteiligten Körper einen Solid haben, also aus einem STEP kommen.
Sonst ist `volume_mm3` gleich `None` und man muss `collides` auswerten. Beim Bau der
Bilder für diese Doku ist genau das passiert:

```
TypeError: unsupported format string passed to NoneType.__format__
```

Ursache war `overlap(backe, machine.body('R15'))` — der Riemen aus dem Maschinen-STL.
Lösung: den Riemen aus dem eigenen STEP nehmen (`p.find('open_belt')`), wie es der
Referenztest tut. Dann steht wieder `volume_mm3=14.07504, exact=1` da.

**`gap` wird bei Durchdringung nicht negativ.** Der Kollisionskern gibt bei Überschneidung
0,0 zurück; wie tief es steckt, sagt `penetrating=True` und, wenn man es genau wissen will,
`overlap(...).max_penetration_mm`. Ein `assert r.min_mm > 0` ist deshalb kein
Durchdringungstest.

**`gap` findet die engste Stelle, nicht die gemeinte.** Der Hopperboden **liegt auf** der
Rahmenauflage (0,0 mm). Misst man die seitliche Luft zur Rahmenwand ohne Fenster, findet
`gap` immer diese Auflage. Es braucht ein `within=Region.box(...)`, das sauber unter der
Auflageebene liegt — im Referenztest bandweise mit 1 mm Sicherheitsabstand, weil die
Auflagefläche selbst geneigt ist und eine achsparallele Box sie sonst wieder mitschneidet.

**Berührung ist nicht Durchdringung.** Kontakte flacher als `TOUCH_TOL_MM = 1e-4` mm zählen
als `touching`, nicht als `collides`. Konstruktiv aufeinanderliegende tesselierte Flächen
liefern in fcl Tiefe 0,0; echte Durchdringungen liegen Größenordnungen darüber. Wer
Formschluss prüft, fragt `touching` ab, nicht `collides`.

**`Region.solid()` und `Region.contains()` gibt es nur für `Region.box`.**
`sample_points()` und `points_local()` nur für `Region.points` / `plane_grid`. Ein
falscher Region-Typ wirft `TypeError`, was gut ist — aber die Fehlermeldung liest man
schneller, wenn man es vorher weiß.

**`Region.crop` teilt Dreiecke, statt sie wegzuwerfen.** Das ist Absicht und nicht
umkehrbar: Maschinen-STLs haben Dreiecke bis 25 mm Kantenlänge. Würde ein Dreieck, das die
Boxwand kreuzt, ganz verworfen, wäre das Messfenster leer und die Prüfung würde
stillschweigend „nichts gefunden" melden. Folge davon: das beschnittene Netz ist nicht
wasserdicht (Schnittflächen bleiben offen). Es taugt für Abstände und Kollisionen, nicht
für Volumenrechnung.

**Die Abtastpunktzahl mit prüfen.** In `test_ecken_geschlossen` steht `assert r.total ==
220`, bevor `r.open` geprüft wird. Verrutscht die Region, wird `total` kleiner, und ohne
diese Zeile bliebe der Test mit weniger Punkten grün.

**`same_as` misst in beide Richtungen.** Eine Richtung allein übersieht hinzugefügtes
Material. Im Quellcode steht dazu, was vorher falsch war: abgetastet wurde aus dem
beschnittenen Netz, gemessen aber gegen das **volle** Gegenstück — die beiden Richtungen
sahen unterschiedliche Geometrie. Heute werden beide Seiten auf dieselbe Region
beschnitten. Größenordnung des Grundrauschens aus der Abtastung: 0,0005 mm.

**Den Vorgängerkörper aus der Szene nehmen.** `machine.scene(hub=hub).without('T05')` —
sonst prüft das neue Teil gegen seinen eigenen Vorgänger, der an derselben Stelle steht,
und jede Kollisionsprüfung schlägt an.

**`moving` muss stimmen.** Bei der Riemenklemme wird der Riemen nach dem Laden bewusst auf
`belt.moving = False` gesetzt, weil er die feste Schleife ist, obwohl das STEP mit
`moving=True` geladen wird. Steht das Kennzeichen falsch, wandert ein Körper in den
Posen-Tests mit, der stehen bleiben müsste, und alle Spalte sind plausibel falsch.

**Ein Zylinderfenster über einem Rundteil misst den Fensterradius, sobald etwas
Dickeres hineinragt.** r 4,5 über dem Zapfen Ø7,9 liefert 3,95. Dasselbe Fenster über den
Bund Ø10,5 verlängert liefert 4,41 — das ist der Fensterradius minus eine Dreieckskante.
Seit Etappe 3 steht `region.meta['rand_schneidet_material']` daneben und im Ergebnis
`fenster_schneidet_material` (Terminal: `~`). Die bessere Antwort ist trotzdem, gar kein
Fenster zu setzen, sondern eine `Interface` zu benennen: dann ist der Bund kein Messwert,
sondern kein Kandidat.

**Bei `Interface` ist ein falsches Maß meist MISSING, nicht FAIL.** Die Suche greift nur
0,25 mm (bzw. 1°) weiter als das Urteil. Ein Radius, der 0,11 mm danebenliegt, wird
gefunden und fällt durch; einer, der 0,55 mm danebenliegt, wird gar nicht erst als
Kandidat angesehen und endet als `MISSING`, also **unentschieden**. Beides ist rot, aber
nur das erste hat einen Messwert. Wer eine Zahl sehen will, muss `tolerance.radius`
weiten — und bekommt dann womöglich `AMBIGUOUS`, weil auch die Nachbarfläche passt.

**`same_as(..., erwartet=...)` nimmt Abtastpunkte heraus, kein Volumen.**
`max_deviation_mm` ignoriert die benannten Regionen, `diff_mm3` zählt sie weiter mit. Das
ist Absicht (sonst verschwände die Größe des erwarteten Unterschieds aus dem Bericht),
überrascht aber, wenn man beide Zahlen nebeneinander liest.

## Form messen

**Konvexität nicht über den Flächenschwerpunkt bestimmen.** Ob eine Kante innen oder
außen ist, entscheidet sich **an der Kante**, nicht am Schwerpunkt der Nachbarfläche. Am
Hopperboden liegen sechs Kanten (0,02 bis 0,57 mm lang) an einer 902 mm² großen Ebene;
deren Schwerpunkt ist 60 mm weit weg und zeigt in die falsche Richtung. Die Sonde muss
lokal messen: Probepunkt neben der Kante, liegt er noch auf der Fläche?

**Die Naht eines Zylinders ist keine unverschmolzene Fläche.** Eine Zylinderfläche
schließt sich an einer Kante mit sich selbst; beide „Nachbarn" sind dieselbe Fläche, der
Knick ist null. An der Wanne sind das 14 Kanten — ohne die Bedingung „zwei verschiedene
Flächen" meldete jeder Rundzapfen Splitter, die keine sind.

**R4,2 gehört nicht an jede scharfe Kante.** Der Rand einer Ø3,4-Bohrung ist geometrisch
eine konvexe 90°-Kante und trotzdem keine Außenkante des Teils: ein R4,2 passt dort
nirgends hin. `unverrundet` nimmt Kreiskanten heraus, deren Krümmungsmittelpunkt nicht im
Material liegt. An der Wanne macht das den Unterschied zwischen 23 gemeldeten und 16
tatsächlichen Kandidaten.

**Abstand 0 ist kein Beleg für eine Kollision.** Formschluss und Durchdringung liefern im
Kollisionskern denselben Wert. Schlimmer: für koinzidente Netze meldet fcl als
Eindringtiefe die volle Körpertiefe — zwei bündige 10er-Würfel ergeben „10 mm". Wer
`penetrating` daraus ableitet, erklärt jede gewollte Auflage zur Kollision (T40 gegen T41
über alle zwölf Posen). Nachgerechnet wird deshalb exakt (Schnittvolumen) oder über die
Tiefe, mit der Stützpunkte **und Facettenmitten** im anderen Körper liegen. Nur die
Stützpunkte reichen nicht: bei zwei Quadern sind die eingedrungenen Punkte genau die Ecken,
und die liegen auf den Seitenflächen des Gegenkörpers — Tiefe 0.

**Ein tangentialer Fillet sieht aus wie eine unverschmolzene Fläche.** Beides ist eine Kante
zwischen zwei Flächen mit Knick 0°. Der Unterschied steht im Flächentyp: geht es auf einen
Zylinder oder Torus, ist der Übergang das Merkmal. Zwei Ebenen dagegen sind eine Boolesche
Spur. Zum Bauen eines Prüfkörpers dafür taugt `a + b` nicht — build123d legt gleichliegende
Ebenen selbst zusammen; man braucht den rohen `BRepAlgoAPI_Fuse` ohne Aufräumen (oder ein
STEP aus fremder Hand, wo genau das fehlt).

**Eine Bettebene je Kante ist immer die Kante selbst.** Wer fragt „liegt diese Kantenmitte am
äußersten Ende der Auflagerichtung?" und dabei nur diese eine Mitte übergibt, bekommt immer
`ja` — das Maximum einer einelementigen Menge ist sie selbst. Der Bezug müssen die Stützpunkte
des ganzen Körpers sein.

**Ein Budget je Messung wird zum Megabyte.** Ein Schwenktest fasst über hundert
Maschinen-STLs an. Schreibt man je Messung eine Zeile „Körper X hat kein BRep", hat der
Tray-Bericht 4749 Einträge und 3 MB. Eine Sammelzeile je Test genügt; die vollständige
Körperliste steht ohnehin unter `budget.koerper`.

## Grün, das nichts bedeutet

**„Nichts gemessen" ist der häufigste stille Fehler.** Region daneben, Schlüssel vertippt,
Fenster zu klein — und der `assert` ist formal erfüllt (`inf > 0.5`). Das Plugin dreht
einen solchen Test wieder auf rot:

```
nichts gemessen: Region enthält keine Geometrie
gap: nichts gemessen: Region enthält keine Geometrie (min_mm=inf, kein Körperpaar im Ausschnitt)
```

Zu korrigieren ist die Region, nicht die Toleranz.

**Fehlt `pruefstand.yaml`, werden die Fixtures übersprungen.** Dann steht am Ende
`skipped` statt `passed` — was leicht als „läuft" gelesen wird. Das Plugin sucht die Datei
von den pytest-Argumenten aus nach oben; ruft man pytest aus einem anderen Ordner auf,
kann sie außerhalb des Suchpfads liegen.

**`xfail` ohne `strict=True` ist wertlos.** Ein bekannter Fehler, der grün wird, muss den
Lauf zum Scheitern bringen. Ohne `strict` verschwindet er als `xpassed` in der
Zusammenfassung.

**Der Marker `warnung` verbirgt keinen Geometriefehler.** Er ist für Druckpose,
Stabilitätsindex und Stil gedacht. Geometrie, Schrauben, Werkzeugzugang und
Montage-Sweeps sind Fehler und sollen das Slicen blockieren. Wer einen roten
Geometrietest mit `@warnung` beruhigt, hebt den Zweck des Werkzeugs auf.

**Toleranzen nicht weichrechnen.** Im Hopperboden steht ein strikter `xfail`, weil an der
hinteren Schrägfläche 0,321 mm statt der geforderten 0,5 mm stehen. Die Toleranz bleibt
auf der Vorgabe, der Test bleibt sichtbar rot, und die Entscheidung liegt bei Marc. Das ist
die richtige Reaktion; die falsche wäre `assert 0.3 <= r.min_mm`.

## Beim Zeichnen von Bildern

**Ein einzelner Schnitt lügt bei schrägen Flächen.** Ein horizontaler Schnitt durch den
geneigten Hopperboden zeigt nur ein schmales Band und sieht aus, als wäre dort keine
Geometrie. Für solche Fälle ist die Projektion aller Dreiecke (Schattenwurf) die ehrlichere
Darstellung; sie steckt in `docs/bilder/src/real_bilder.py` als `schatten()`.

**Maßpfeil und Beschriftung müssen dieselbe Strecke meinen.** Im Bild zur Riemenklemme
stand erst „13,5 mm Luft" über einem Pfeil, der 12,8 mm lang war, weil er am Riemenrücken
statt an der Zahnspitze ansetzte. Solche Abweichungen sieht man nur, wenn man das erzeugte
Bild wirklich ansieht.
