# OCCT robuster und erheblich schneller machen — Idee zur Bewertung

Stand 18.09.2026, Marc Neuhaus / Fable. Zur Zweitmeinung (Astra). Status: Idee, nicht beauftragt.

## Ausgangslage

Wir konstruieren Druckteile und Maschinen (Onshape, FeatureScript, lokal build123d/OCCT) und
prüfen sie offline mit einem eigenen pytest-Werkzeug `pruefstand` (STEP + OCCT-Booleans für
Urteile, fcl/VTK-Meshes für Suche). Wiederkehrende Kernelprobleme in OCCT 7.8/7.9 über
build123d: stille No-Op-Fillets, Booleans, die je nach Reihenfolge scheitern
(„Boolean-Lotterie"), harte Abstürze (Signal, nicht Exception — wir sperren Booleans deshalb
in einen Spawn-Prozess), `BinTools`-Pickle-Bruch an echten STEP-Körpern. Modelliert wird
darum in Onshape (Parasolid); OCCT misst nur. Fernwunsch: nicht auf Parasolid angewiesen sein,
und: „es darf immer gerne schneller sein".

## Die Idee: Differential Testing mit Parasolid als Orakel

1. **Korpus.** Jeder Kernelfehler, den `pruefstand` oder cad-khana einfängt, wird ein Fall:
   Eingangskörper als STEP, eine Operation (Fillet r an Kanten X / Union A,B / Cut), OCCTs
   Ergebnis (Volumen, Flächenzahl, Status, Absturz) und **dieselbe Operation in Onshape**
   gebaut → Sollwert (STEP, Volumen, Topologie). Kosten je Fall: ein Feature + ein Export.
2. **Umgehungen.** Mit Sollwert systematisch probieren: Fuzzy-Wert, n-äre Booleans
   (`BOPAlgo_Builder`, ein Durchgang statt paarweiser Kette), Reihenfolge, Flächen vorher
   splitten, `BRepAlgoAPI` direkt statt Wrapper. Treffer werden Assertions/Regeln in cad-khana.
3. **Patches.** Reproduzierer + Sollwert + Profil je Fall → gezielte Änderungen in
   `BOPAlgo`/`IntPatch`/`ChFi3d`, gegen OCCTs Testsuite, upstream. Fables Schätzung: vielleicht
   1 von 5 Fällen patchbar; erst ab ~20 Korpusfällen sinnvoll.

## Beschleunigung — Ebenen mit erwartetem Faktor

- **Ebene 0, messen:** Profil über echte Läufe. Eigenes Beispiel: 476 ms je Schnitt, davon
  470 ms BREP-Lesen; mit Cache 6,8 ms (×70) ohne eine Zeile OCCT.
- **Ebene 1, OCCT richtig nutzen (×3–10 für unsere Lasten):** `SetRunParallel(true)` bei
  Booleans und `BRepMesh` (build123d schaltet es nicht ein); n-äre Booleans statt Ketten
  (schneller *und* robuster); OCCT nativ mit `-O3 -march=native`, LTO, TBB bauen (+10–30 %).
- **Ebene 2, algorithmisch fürs Messen (×100):** exakte parallele Mesh-Booleans (Manifold,
  OpenSCAD-Kern) für Kollision/Volumen; B-Rep nur fürs Urteil. `pruefstand` tut das teils.
- **Ebene 3, der Kern selbst:** BVH durchgängig im Pave-Filler statt paarweiser
  Kandidatenprüfung, bessere Startwerte in Flächen-Flächen-Schnitten, tolerante Topologie
  mit weniger Reparaturläufen. Braucht den Korpus als Messgrundlage.

## Fragen an Astra

1. Ist Differential Testing gegen Parasolid der richtige Hebel, oder gibt es einen
   bekannteren Weg zu robusteren OCCT-Booleans/Fillets (z. B. bestehende Forks, OCCT-Roadmap)?
2. Wie realistisch sind Patches in `BOPAlgo`/`ChFi3d` durch LLM-gestütztes Debugging mit
   Reproduzierer + Sollwert? Wo liegen die bekannten Wurzeln der Fehler?
3. Welche der Beschleunigungsebenen ist unterschätzt oder überschätzt? Gibt es Zahlen zu
   `SetRunParallel` und n-ären Booleans an realen Teilen?
4. Gibt es einen offenen B-Rep-Kernel jenseits OCCT, der die Robustheitslücke zu Parasolid
   schließt, oder ist das nachweislich nicht in Reichweite?
5. Kernel selbst schreiben (Kategorie D unserer Research): begründet ausgeschlossen?
