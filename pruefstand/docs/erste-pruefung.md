# Die erste eigene Prüfung

Schritt für Schritt, mit echten Ausgaben. Alle Befehle unten sind so gelaufen; die
Beispiele arbeiten gegen den Maschinenkontext der R6d, weil der vorhanden ist.

## Schritt 0: Was vorhanden sein muss

- ein STEP des neuen Teils, üblicherweise `<projekt>/native/<teil>-native.step`,
- ein Maschinenkontext `machine.json` der Revision, in die das Teil eingebaut wird,
- der Prüfstand selbst, einmal eingerichtet:

```bash
cd /Users/mneuhaus/Workspace/cad/toolroom/pruefstand
uv sync
```

`python3` ist im Shell-Profil umgebogen. Alles läuft über `uv run python …` oder
`uv run pytest …`.

## Schritt 1: pruefstand.yaml

Im Ordner `spec/` des Projekts, neben den Tests. Pfade sind relativ zu dieser Datei.

```yaml
machine: ../../rocking-photo-tray-r6d/machine/machine.json
review: ../var/review        # optional, Default <projekt>/var/review
```

Das Plugin sucht diese Datei von den pytest-Argumenten aus nach oben. Fehlt sie, werden
die Fixtures `project` und `machine` übersprungen — die Tests gehen dann auf `skipped`,
nicht auf grün.

Damit stehen zwei Session-Fixtures bereit:

- `project` mit `.root` (Projektordner), `.spec` und `.review`,
- `machine`, die geladene `Machine`.

## Schritt 2: nachsehen, was in der Maschine steckt

Bevor man Körperschlüssel in einen Test schreibt, sieht man sie sich an. Ein Wegwerftest
genügt:

```python
def test_koerper_zeigen(machine):
    print(len(machine.keys()), machine.keys()[:8])
    print(machine.motions)
```

```
uv run pytest spec -q -s
102 ['R00', 'R01', 'R02', 'R03', 'R05', 'R06', 'R07', 'R08']
{'hub': {'kind': 'translation', 'frame': 'local', 'axis': [0, 0, 1], 'range': [0, 130], 'default': 0}}
```

102 Körper, eine Bewegung `hub` von 0 bis 130 mm entlang lokal Z. Was welcher Schlüssel
ist, steht in `machine.json` (`name`, `role`).

## Schritt 3: das Teil laden

```python
import pytest
from pruefstand import load_step

@pytest.fixture(scope='module')
def t05(project):
    return load_step(project.root / 'native/hopper-floor-r1-native.step').one(key='T05', moving=False)
```

`load_step` gibt `Parts` zurück, eine Sammlung. `one(key=…)` erzwingt genau einen Körper
und benennt ihn, `find('teil')` sucht über einen Namensbestandteil, `find_all` liefert
alle Treffer (so kommen die vier M3-Schrauben der Riemenklemme in den Test).

`moving=` sagt, ob der Körper bei einer Pose mitwandert. Das muss stimmen, sonst messen
die Posen-Tests gegen eine stehende Kopie.

## Schritt 4: den ersten Test schreiben — und rot sehen

Ein Test schreibt man als Behauptung mit Zahl, nicht als Frage. Absichtlich mit falscher
Toleranz, um zu sehen, dass er wirklich misst:

```python
from pruefstand import gap

def test_spalt_zur_rueckwand(machine):
    r = gap(machine.body('T05'), machine.body('T06'))
    assert r.min_mm >= 1.0, r
```

```
uv run pytest spec -q

E       AssertionError: gap(min_mm=0.2, penetrating=0)
E       assert 0.1999969482421875 >= 1.0
E        +  where 0.1999969482421875 = gap(min_mm=0.2, penetrating=0).min_mm
---------------------------------- pruefstand ----------------------------------
  failed test_spalt_zur_rueckwand gap(min_mm=0.2, penetrating=0)
Bericht: /private/tmp/ps-demo/var/review/pruefstand.json
1 failed in 0.36s
```

Das ist der Moment, der den Prüfstand ausmacht: die Meldung nennt den Messwert (0,2 mm),
die beteiligten Körper und den Pfad zum Bericht. Jetzt entscheidet man — ist 0,2 mm
richtig, dann kommt die Toleranz auf 0,2; ist sie falsch, kommt die Geometrie dran.

Die ganze Messung steht danach in `var/review/pruefstand.json`, auch die, die man im
Terminal nicht sieht:

```json
{
  "primitive": "gap",
  "min_mm": 0.2,
  "pair": ["T05", "T06"],
  "penetrating": 0,
  "point_a": [-124.6, -117.8, 242.0572],
  "point_b": [-124.6, -118.0, 242.0572],
  "per_body": {"T06": 0.2}
}
```

`point_a` / `point_b` sind Weltkoordinaten der engsten Stelle. Wenn man nicht versteht,
wo gemessen wurde, sieht man sich diese zwei Punkte an.

## Schritt 5: die Toleranz festschreiben und begründen

```python
def test_spalt_zur_rueckwand_unveraendert(t05, t05_alt, machine):
    """Hinterer Rand zu T06 wie in R6d: 0,2 mm, alt und neu identisch."""
    neu = gap(t05, machine.body('T06'))
    alt = gap(t05_alt, machine.body('T06'))
    assert 0.15 <= neu.min_mm <= 0.3, neu
    assert abs(neu.min_mm - alt.min_mm) < 0.02, (neu, alt)
```

Drei Gewohnheiten aus den beiden Referenzprojekten:

- **Intervall statt einseitiger Schranke.** `0.15 <= x <= 0.3` fällt auch auf, wenn der
  Spalt zu groß wird. `x > 0.15` deckt das nicht ab.
- **Der Docstring nennt die Sollzahl und woher sie kommt.** Er ist die Begründung, die man
  in einem halben Jahr braucht.
- **Gegen den Vorgänger vergleichen, wo nichts geändert werden sollte.** Das fängt
  Kollateralschäden, die man nicht gesucht hat.

## Schritt 6: über die Posen parametrisieren

Ein Spalt, der in einer Stellung passt, kann in einer anderen zu sein.

```python
@pytest.mark.parametrize('hub', [0, 65, 130])
def test_keine_durchdringung_mit_der_maschine(t05, machine, hub):
    r = overlap(t05, machine.scene(hub=hub).without('T05'))
    assert not r.collides, r
```

`without('T05')` nimmt den Vorgängerkörper aus der Szene — sonst prüft man das neue Teil
gegen sich selbst.

## Schritt 7: bekannte Fehler festnageln

Sobald ein Fehler gefunden ist, wird er zur zweiten Variante desselben Tests. Der
Vorgängerkörper aus dem Maschinenkontext ist dafür schon da.

```python
VARIANTEN = ['R1', pytest.param('R6d', marks=pytest.mark.xfail(
    strict=True, reason='R6d: Lücke neben den Wagen'))]
```

`strict=True` heißt: wird der alte Fehler grün, scheitert der Lauf. Ein bekannter Fehler,
der sich nicht mehr reproduzieren lässt, ist ein Grund nachzusehen, kein Grund zur Freude.

## Wenn der Test grün ist und es nicht sein dürfte

Erst nachsehen, ob überhaupt gemessen wurde. Eine Region, die neben dem Teil liegt, wird
vom Prüfstand erkannt:

```python
def test_leere_region(machine):
    daneben = Region.box(machine.frame('local'), (300, 300, 300), (310, 310, 310))
    r = gap(machine.body('T05'), machine.body('T06'), within=daneben)
    assert r.min_mm > 0.5, r
```

```
nichts gemessen: Region enthält keine Geometrie
gap: nichts gemessen: Region enthält keine Geometrie (min_mm=inf, kein Körperpaar im Ausschnitt)
  failed test_leere_region gap(min_mm=inf, penetrating=0, nichts_gemessen=True)
1 failed, 1 passed in 0.29s
```

Der `assert` wäre erfüllt gewesen (`inf > 0.5`). Der Test fällt trotzdem durch. Zu
korrigieren ist die Region, nicht die Toleranz.

## Ein ganzes Projekt prüfen

```bash
cd /Users/mneuhaus/Workspace/cad/step-feeder/rocking-photo-tray-r6d-hopper-floor-r1
uv run --project /Users/mneuhaus/Workspace/cad/toolroom/pruefstand pytest spec -q
```

Am Ende steht je Test eine Zeile mit den ersten drei Kennzahlen, dann der Pfad zum
Bericht. Der Lauf vom 17.09.2026:

```
23 passed, 2 xfailed, 4 warnings in 8.71s
```

Weiter: [fallstricke.md](fallstricke.md) sammelt, was daran schon Zeit gekostet hat.
