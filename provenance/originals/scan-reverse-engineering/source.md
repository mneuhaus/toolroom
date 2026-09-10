---
name: scan-reverse-engineering
description: 3D-Scans (STL/PLY, Revopoint) in sauberes parametrisches CAD zurückführen — Scans säubern, registrieren, kanonisch ausrichten, Primitive fitten (Kegel/Zylinder/Ebene/Kugel), Konturen entrauschen, Grundform von Features trennen und die Rekonstruktion gegen die Scan-Außenhaut messen. Laden BEVOR ein Scan vermessen oder nachgebaut wird (Trigger "Scan nachbauen", "aus STL rekonstruieren", "Reverse Engineering", *.stl aus Revopoint/Einscan).
---

# Scan → parametrisches CAD

Toolkit: `~/Workspace/cad/scan-toolkit/` (flache Module, kein Paket — Skripte
setzen `sys.path[:0] = [<eigenes src>, '<user-home>/Workspace/cad/scan-toolkit']`).
Referenz-Projekt: `~/Workspace/cad/linak-gehaeuse/` (LINAK-Motorhaube).
Läuft unter **Python 3.12** (open3d hat keine 3.13-Wheels) — `uv` mit
`requires-python = ">=3.12,<3.13"`, Deps: numpy scipy open3d trimesh matplotlib
pillow rtree.

## Reihenfolge, die sich bewährt hat

**0. FOTOS ZUERST.** Vor jeder Vermessung Fotos des realen Teils anschauen bzw.
anfordern. Aus Scans allein habe ich beim LINAK-Gehäuse über eine Stunde lang
die Topologie falsch interpretiert; ein Foto hat es in Sekunden geklärt.
Fotos zeigen außerdem, was **kein** Formmerkmal ist — die runden „Dellen" waren
aufgeklebte Revopoint-Marker.

1. **Sichten** — `views.py` (6 Achsenansichten) und `spin.py` (12er-Orbit).
   Beide splatten flächengewichtet Punkte INNERHALB der Dreiecke; CAD-Exporte
   bestehen aus wenigen Riesendreiecken, Schwerpunkt-Splatting lässt die
   Fläche löchrig aussehen.
2. **Säubern** — `clean.py` (Drehteller unter einer Höhe wegschneiden, dann
   Komponenten) bzw. `clean2.py` (RANSAC-Ebene + DBSCAN). Achtung: der
   Revopoint-Output ist **nicht lotrecht** — der Drehteller kann senkrecht zu
   Y liegen. Ebenensuche orientierungsunabhängig führen, nicht „z ≈ 0"
   annehmen. Markerkugeln über den bbox-Durchmesser aussortieren.
3. **Registrieren** — `reg.py` (FPFH+RANSAC global → ICP point-to-plane in
   drei Auflösungsstufen). Fitness > 0,7 und RMSE < 0,3 mm heißt „gleiches
   Teil, gleiche Lage". Scans mit viel Drehteller registrieren schlecht —
   erst säubern.
4. **Kanonisch ausrichten** — `primitives.py`-Achsenhypothesen liefern meist
   ein orthogonales Tripel (Hauptachse, Querachse, Ebenennormale). Danach die
   Achse über die **Mittelpunkte scheibenweiser Kreisfits** nachjustieren, nicht
   über Normalen allein.
   *Falle:* `xs = vc[:,0]` ist ein VIEW — nach `vc[:,0] -= xs.min()` ist
   `xs.min()` schon 0. Offsets vorher als float sichern.
5. **Vermessen** — `sections.py` (echte Konturschnitte), `zoom`-Plots mit
   feinem Raster zum Ablesen, `fitlib.py` (Kreis/Ebene mit Ausreißer-
   Verwerfung), `primitives.py` (Efficient-RANSAC für Ebene/Zylinder/Kegel/
   Kugel).
6. **Grundform von Features trennen** — `decompose.py`: Graustufen-Morphologie
   auf dem Polarradius R(θ). `opening` entfernt schmale konvexe Wülste,
   `closing` füllt schmale konkave Nuten. Die Differenz IST das Feature und
   wird im CAD als eigenes parametrisches Element gebaut.
7. **Abgleichen** — `outer_ref.py` (dichte Punktwolke NUR der Außenhaut, über
   Polar-Max je Schnitt — Innenrippen fallen raus) + `diff2.py` (beidseitige
   Abweichung + Karte). Median/p90 sind die Kennzahlen, nicht max.

## Werkzeuge im Detail

| Modul | Zweck |
|---|---|
| `meshio.py` | schnelles Binär-STL lesen/schreiben, `weld`, `components`, `face_props`, `submesh` |
| `fitlib.py` | `fit_circle`, `fit_plane` mit iterativer Ausreißer-Verwerfung |
| `sections.py` | Dreieck-Ebenen-Schnitt → Segmente; Mehrfach-Stationen-Plots |
| `contour.py` | `outer_contour` — Polar-Max je Winkel-Bin, Lücken interpoliert, zirkulär geglättet; `resample` |
| `decompose.py` | Graustufen-Morphologie (`opening`/`closing`/`base_profile`) |
| `primitives.py` | Efficient-RANSAC-Segmentierung + Least-Squares-Refits |
| `clean.py` / `clean2.py` | Drehteller + Markerkugeln entfernen |
| `reg.py` | globale Registrierung + ICP (open3d) |
| `merge.py`, `apply_T.py`, `crop.py` | Transformationen anwenden, zusammenführen, zuschneiden |
| `holes.py` | offene Randschleifen finden → echte Durchbrüche vs. Scanlöcher |
| `views.py`, `spin.py` | Ansichten / Orbit-Kontaktbogen |
| `outer_ref.py`, `diff2.py` | Referenzhaut + Abweichungsmessung |
| `fus.py` | Fusion-MCP-Client mit 900 s Timeout (khanas `fcall.py` bricht bei 300 s ab) |

### Kegel-Refit (der Trick, der die Segmentierung erst brauchbar macht)
Zwei exakte lineare Fakten machen ihn robust:
* alle Flächennormalen schließen denselben Winkel mit der Achse ein → Achse
  allein aus den Normalen (SVD der zentrierten Normalen),
* die Spitze liegt in JEDER Tangentialebene: `N_i · (apex − p_i) = 0` → apex
  per `lstsq`.
Ohne diesen Refit zerlegen Kugelfits einen Kegel in Bänder (eine Kugel r≈33
passt lokal über 14 mm auf 0,35 mm genau) und die Segmentierung wird Müll.

## Design Intent statt Punktwolke

Ziel ist **nicht** maximale Deckung mit dem Scan, sondern die einfachste Form,
die das Bauteil funktional ersetzt. Konkret:

* **Rationalisieren.** Der LINAK-Korpus misst sich als leicht balliger Kegel
  (+0,2 mm Bauch über 90 mm). Das ist Schwindung, kein Konstruktionsmerkmal →
  als gerader Kegel mit 1,25° Formschräge bauen.
* **Formschrägen suchen.** Radius über der Achse auftragen (`profile.py`).
  Sauber lineares dR/dx = Entformschräge; die gehört ins Modell, nicht
  wegmitteln.
* **Funktionsflächen zuerst.** Passungen, Kanäle, Löcher, Auflageebenen exakt;
  Kosmetik darf 0,5–1 mm daneben liegen.
* **Symmetrien und Koinzidenzen prüfen** — sie verraten die Konstruktion. Beim
  LINAK-Gehäuse fitten beide Wanddurchbrüche des Querkanals auf x = 126,15,
  also liegt die Kanalachse EXAKT in der Mündungsebene. Ein Parameter statt
  zwei.
* **Vereinfachungs-Hypothesen messen, nicht glauben.** „Kopf = 2-Profil-Loft
  mit Tangenten" klang plausibel, lag aber im Median 2,0 mm daneben →
  verworfen. Umgekehrt hielt „Abrollung = ein Kreisbogen R=32,9" mit RMS
  0,18 mm über 33 mm. Immer erst rechnen.

## Fallen

* **Polar-Max überbrückt Hinterschnitte.** `outer_contour` liefert je Strahl
  den äußersten Treffer — Kanäle und Taschen werden zugedeckt. Das ist beim
  Bau der Grundform ERWÜNSCHT (die Tasche kommt danach als Schnitt), beim
  Vermessen aber eine Fehlerquelle.
* **Randschleifen ≠ Scanlöcher.** Über `holes.py` klassifizieren: eine glatte
  Schleife mit Umfang ≈ Kreisumfang ist ein echtes Loch, eine zerfranste mit
  doppeltem Umfang ist ein Scanloch.
* **Scan-Marker** sitzen ~0,1–0,2 mm über der Fläche und heben den
  Polar-Max-Radius leicht an. Bei Toleranzen < 0,3 mm relevant.
* **STL-Sampling für Abweichungen** muss INNERHALB der Dreiecke ziehen. Sonst
  misst man die Tessellierung des CAD-Exports statt der Geometrie.
