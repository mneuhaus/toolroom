# FeatureScript-Lektionen fuer den Vorpruef-Linter

Diese Datei ist die Regel-Datenbank hinter `fs_lint.py`
(`toolroom/skills/onshape-cad/scripts/fs_lint.py`). Jeder Eintrag entspricht
einer Regel-ID im Linter: Symptom -> Ursache -> lokale Vorprüfung.
Neue Regeln FS016–FS030 sind konservative, synthetisch getestete Heuristiken;
nicht jeder beschriebene Fehler wurde live auf Onshape reproduziert. Dieser
Review hat ausdrücklich keine Onshape-/Bridge-Aufrufe ausgeführt.

## Wie ein neuer Eintrag entsteht

1. Ein FS-Upload scheitert in Onshape, oder ein stiller Fehler faellt erst im
   Part Studio auf (0 Teile, verschwundene Geometrie, No-Op-Feature).
2. Fehlertext/Symptom hier notieren, Ursache klaeren (siehe
   `skills/onshape-cad/references/field-notes.md` und
   `skills/onshape-cad/references/revision-workflow.md`).
3. In `fs_lint.py` eine neue `_rule_fsNNN`-Funktion ergaenzen und mit
   `@rule("FSNNN", severity, "...")` registrieren.
4. Testfall (positiv + negativ) in `pruefstand/tests/test_fs_lint.py`.

## Regeln

### FS001 -- Kopf und std-Importversion
- **Symptom:** Parsefehler beim Header oder unerwartetes Verhalten einer Standardbibliothek.
- **Ursache:** Header fehlt/steht hinter Code; ein expliziter `// Functions-only fragment`-Marker kennzeichnet bewusst importierte Fragmente; kopierter Import verwendet eine andere Revision. Abweichende Versionen sind nicht automatisch ein Compilerfehler.
- **Lint-Regel:** FS001, ERROR bei fehlendem Header als erster Anweisung; WARN bei abweichender numerischer std-Version. Importreihenfolge und Kommentare werden berücksichtigt.
- **Testreferenz:** `test_fs001_reordered_import_keys_and_comment`.

### FS002 -- Doppelte Erzeuger-ID
- **Symptom:** Zweite Geometrieoperation kann wegen bereits verwendeter ID scheitern.
- **Ursache:** Mehrere Erzeuger erhalten denselben vollständigen literalen Kind-ID-Ausdruck. IDs werden nicht still überschrieben.
- **Lint-Regel:** FS002, ERROR im geradlinigen Funktionskörper; Query-Lesezugriffe zählen nicht. Dynamische IDs und verzweigte Blöcke werden nicht als bewiesene Kollision behandelt.
- **Testreferenz:** `test_fs002_noncolliding_id_expressions`.

### FS003 -- Konstante ID in Schleifen
- **Symptom:** Eine spätere Iteration kollidiert mit der vorherigen Operation.
- **Ursache:** Erzeuger-ID enthält keinen variablen Iterationsanteil.
- **Lint-Regel:** FS003, WARN für for/while mit konstantem vollständigem ID-Argument, auch bei size()-Aufrufen im Header. qCreatedBy liest nur. Lokal mit unstableIdComponent oder variabler ~-Verkettung abgeleitete IDs werden ausgenommen.
- **Testreferenz:** `test_fs003_loop_local_unstable_id_component_is_not_constant`.

### FS004 -- Translationsvektor ohne Einheit
- **Symptom:** Einheitenfehler beim Verschieben oder falsche Maßannahmen.
- **Ursache:** Dimensionsloser Zahlenvektor wird als Länge benutzt.
- **Lint-Regel:** FS004, WARN; bei transform zählt die Translation, auch vector(1,1,1). Äußere Klammern/Matrixprodukte mit Längeneinheit werden berücksichtigt. Lokale Helfer sind ausgenommen.
- **Testreferenz:** `test_fs004_transform_translation_units`.

### FS005 -- Vertauschte oder degenerierte Box-Ecken
- **Symptom:** Leere Region, Nullstärke oder unerwartete Box.
- **Ursache:** Min-/Max-Ecken sind vertauscht oder in einer Achse gleich. Helfer können diese Ecken allerdings selbst sortieren.
- **Lint-Regel:** FS005, WARN, kein sicherer Fehler: nur lokal deklarierte box/block-Helfer mit numerischen Vektoren. Der Vertrag des Helfers bleibt unbekannt.
- **Testreferenz:** `test_fs005_degenerate_corner_is_advisory`.

### FS006 -- Ebenen-Normalen und Achsen
- **Symptom:** Ungültige Ebene oder unerwartete Orientierung.
- **Ursache:** Numerischer Normalen-/Achsenvektor ist nicht normiert.
- **Lint-Regel:** FS006, WARN bei Betrag außerhalb 1 ± 0,01, einschließlich Nullvektor. Zwei-/Drei-Argument-plane und darin verschachtelte opPlane-Definitionen werden geprüft; berechnete Normalen nicht.
- **Testreferenz:** `test_fs006_two_argument_and_opplane`.

### FS007 -- Query-Nutzung nach Boolean
- **Symptom:** Folgeoperation erhält veränderte oder konsumierte Geometrie.
- **Ursache:** Eine lazy Query kann nach einer Topologieänderung andere oder keine Entitäten liefern. Targets können aber legitim erhalten bleiben; qCreatedBy ist keine pauschale Reparatur.
- **Lint-Regel:** FS007, WARN für direkte Nutzung in Geometrieaufrufen ohne Neuzuweisung innerhalb derselben Funktion. keepTools:true, String-Inhalte und reine Query-Komposition werden ausgenommen.
- **Testreferenz:** `test_fs007_query_composition_is_not_a_geometry_read`.

### FS008 -- Rib-Helfer prüfen
- **Symptom:** Rippe bindet nicht sauber an oder Parameterreihenfolge passt nicht.
- **Ursache:** Projektbezogene rib-Helfer können problematische Überlappungen haben.
- **Lint-Regel:** FS008, INFO als manuelle Prüfliste, keine Aussage über bewiesene geometrische Fehler.
- **Testreferenz:** `test_fs008_rib_call_flagged_as_info`.

### FS009 -- Leere Boolean-Tools
- **Symptom:** Boolean kann keine Werkzeugkörper verarbeiten.
- **Ursache:** tools ist ausdrücklich leer.
- **Lint-Regel:** FS009, ERROR für [], qUnion([]) oder qNothing() als oberstes tools-Feld einer literalen Optionsmap.
- **Testreferenz:** `test_fs009_qnothing`.

### FS010 -- Extrude ohne endBound
- **Symptom:** Extrusionsgrenze fehlt oder entspricht nicht der Absicht.
- **Ursache:** Optionsmap enthält keinen expliziten endBound.
- **Lint-Regel:** FS010, WARN; nur tatsächliches Top-Level-Map-Feld zählt, nicht gleichnamiger String im ID-Argument. Berechnete Maps bleiben ungeprüft.
- **Testreferenz:** `test_fs010_endbound_id_string_does_not_supply_map_key`.

### FS011 -- Feature-Annotation zuordnen
- **Symptom:** Feature hat keinen sinnvollen Anzeigenamen oder ist nicht wie beabsichtigt registriert.
- **Ursache:** Feature Type Name-Annotation fehlt direkt vor seiner Deklaration.
- **Lint-Regel:** FS011, ERROR für direkt deklarierte defineFeature-Konstanten ohne zugeordnete Annotation. Parameter dürfen anders heißen; reine Bibliotheksmodule brauchen kein defineFeature.
- **Testreferenz:** `test_fs011_unrelated_annotation_after_feature_cannot_hide_error`.

### FS012 -- Lexikalische Fehler und Klammern
- **Symptom:** FeatureScript-Quelle lässt sich nicht parsen.
- **Ursache:** Unpassende Klammer oder nicht abgeschlossener String/Blockkommentar.
- **Lint-Regel:** FS012, ERROR; Kommentar-/String-Inhalte beeinflussen die Klammerbilanz nicht. Escapes erhalten die Quelltextposition.
- **Testreferenz:** `test_fs012_unterminated_lexemes`.

### FS013 -- Tabs und typografische Anführungszeichen
- **Symptom:** Stilabweichung oder ungültige String-Delimiter nach Copy/Paste.
- **Ursache:** Tabs in Code-Einrückung bzw. Smart Quotes außerhalb von Kommentaren/Strings.
- **Lint-Regel:** FS013, WARN für Einrückungs-Tabs (Tabs sind nicht pauschal ungültig); ERROR für typografische Quotes im Code.
- **Testreferenz:** `test_fs013_tabs_inside_string_or_comment_are_not_indentation`.

### FS014 -- Quelltext-/Operationsbudget
- **Symptom:** Großes Feature ist schwerer zu warten; mögliche Regenerationsprobleme.
- **Ursache:** Große Quelldatei oder viele direkte Erzeugeraufrufe.
- **Lint-Regel:** FS014, WARN über 200.000 UTF-8-Bytes bzw. 5.000 Erzeugeraufrufen. Quellgröße ist keine gemessene Regenerationszeit; Query-IDs zählen nicht als Operationen.
- **Testreferenz:** `test_fs014_large_op_count_flagged`.

### FS015 -- Unbekannte Funktionsnamen
- **Symptom:** Möglicher Unresolved-reference-Fehler.
- **Ursache:** Tippfehler, fehlender Import oder unvollständige lokale Wissensbasis.
- **Lint-Regel:** FS015, WARN für unbekannte Namen, nur Code wird durchsucht. Lokale/zugewiesene Funktionen, std-Inventar, Member-/Namespace-Aufrufe und silent-Syntax werden berücksichtigt. Importauflösung bleibt unvollständig.
- **Testreferenz:** `test_fs015_string_cannot_declare_function`.

### FS016 -- Helfer-ID ohne Aufruf-Suffix
- **Symptom in Onshape:** Mehrfach aufgerufener lokaler Geometriehelfer meldet eine doppelte Feature-ID.
- **Ursache:** Der Helfer bekommt bei mehreren Aufrufen dieselbe unveränderte ID.
- **Lint-Regel:** FS016 (WARN), wiederholte lokale Helferaufrufe mit identischer Id im selben lexikalischen Scope; nur Helfer mit expliziten Context-/Id-Parametern zählen als Erzeuger, nicht mathematische Funktionen.
- **Testreferenz:** `test_fs016_helper_id_namespace`.

### FS017 -- Boolean Target gleich Tool
- **Symptom in Onshape:** `BOOLEAN_BAD_INPUT`, leere Geometrie oder stiller No-Op.
- **Ursache:** `targets` und `tools` sind textuell dieselbe Query.
- **Lint-Regel:** FS017 (ERROR bei SUBTRACTION, WARN bei UNION).
- **Testreferenz:** `test_fs017_same_boolean_query`.

### FS018 -- Gelöschte Query weiterverwenden
- **Symptom in Onshape:** Nach `opDeleteBodies` arbeitet eine Folgeoperation mit einer leeren Query.
- **Ursache:** Query-Ausdrücke sind lazy und zeigen nach dem Löschen nicht mehr auf den Körper.
- **Lint-Regel:** FS018 (WARN), gelesene Query-Variable nach dem Löschen ohne Neuzuweisung.
- **Testreferenz:** `test_fs018_deleted_query_reuse`.

### FS019 -- qCreatedBy ohne lokalen Erzeuger
- **Symptom in Onshape:** `qCreatedBy` liefert leer, obwohl die Id scheinbar korrekt aussieht.
- **Ursache:** Tippfehler oder falscher Id-Namensraum.
- **Lint-Regel:** FS019 (WARN), nur bei literalem Id-Ausdruck und ohne vorherigen lokalen Erzeuger.
- **Testreferenz:** `test_fs019_unknown_creation_id`.

### FS020 -- Fehlender EntityType
- **Symptom in Onshape:** Nachfolgende Operation erhält unerwartete Entity-Arten oder mehrere Treffer.
- **Ursache:** `qCreatedBy` ohne optionalen EntityType-Filter.
- **Lint-Regel:** FS020 (INFO), gültige Overloads bleiben erlaubt.
- **Testreferenz:** `test_fs020_optional_entity_type`.

### FS021 -- Zu wenige Loft-/Sweep-Profile
- **Symptom in Onshape:** Loft/Sweep meldet fehlende oder leere Profile.
- **Ursache:** Literal leere Query, ein Loft-Profil oder fehlender Sweep-Pfad.
- **Lint-Regel:** FS021 (ERROR), nur statisch erkennbare Maps und Literale.
- **Testreferenz:** `test_fs021_profiles_and_path`.

### FS022 -- Precondition-Typ erneut skalieren
- **Symptom in Onshape:** Länge/Winkel wird doppelt mit einer Einheit skaliert.
- **Ursache:** `isLength`/`isAngle` validiert bereits den Parametertyp, spätere Multiplikation ist oft ein Einheitenfehler.
- **Lint-Regel:** FS022 (WARN), lexikalischer Hinweis ohne vollständige Typanalyse.
- **Testreferenz:** `test_fs022_precondition_units`.

### FS023 -- Parameter ohne Name-Annotation
- **Symptom in Onshape:** Feature-Dialog zeigt unlesbare oder fehlende Parameternamen.
- **Ursache:** Sichtbarer Precondition-Parameter hat keine `annotation { "Name": ... }`.
- **Lint-Regel:** FS023 (WARN).
- **Testreferenz:** `test_fs023_parameter_annotation`.

### FS024 -- Leere regenError-Meldung
- **Symptom in Onshape:** Regeneration bricht ohne verwertbare Fehlermeldung ab.
- **Ursache:** `regenError` wird mit leerem String aufgerufen.
- **Lint-Regel:** FS024 (WARN); aussagekräftige Strings und Enum-Werte bleiben erlaubt.
- **Testreferenz:** `test_fs024_regenerror_strings`.

### FS025 -- Catch ohne Rethrow
- **Symptom in Onshape:** Fehler wird verschluckt, Feature erscheint scheinbar erfolgreich.
- **Ursache:** `catch` protokolliert nur oder bleibt leer.
- **Lint-Regel:** FS025 (WARN), absichtliche Fallbacks müssen manuell geprüft werden.
- **Testreferenz:** `test_fs025_catch_without_rethrow`.

### FS026 -- Falsche size-Schleifengrenze
- **Symptom in Onshape:** Zugriff auf ein Element außerhalb des Arrays.
- **Ursache:** Bei Indexstart 0 ist `<= size(array)` um eine Iteration zu lang.
- **Lint-Regel:** FS026 (WARN), `i < size(...)` bevorzugen.
- **Testreferenz:** `test_fs026_size_loop_bounds`.

### FS027 -- Unbenutzte lokale Variable
- **Symptom in Onshape:** Parameteränderung wirkt nicht oder Copy-Paste-Rest bleibt im Feature.
- **Ursache:** Variable wird initialisiert, aber lexikalisch nicht gelesen.
- **Lint-Regel:** FS027 (INFO), Seiteneffekte der Initialisierung können beabsichtigt sein.
- **Testreferenz:** `test_fs027_unused_local_variable`.

### FS028 -- Helfer-Argumentzahl
- **Symptom in Onshape:** FeatureScript meldet keine passende Funktionssignatur.
- **Ursache:** Lokaler Helfer wie `yz`, `lb` oder `prism` wird mit falscher Argumentzahl aufgerufen.
- **Lint-Regel:** FS028 (ERROR für eindeutig lokale Namen, WARN bei zusätzlichen möglichen std-Overloads), lokale Signaturen und verschachtelte Klammern werden berücksichtigt; auch block/cylinder werden nicht mehr pauschal übersprungen.
- **Testreferenz:** `test_fs028_local_helper_arity`.

### FS029 -- std-Namenskonflikt
- **Symptom in Onshape:** Ein Helfer ruft scheinbar die Standardfunktion auf, tatsächlich wird lokale Logik verwendet.
- **Ursache:** Lokale Funktionen heißen `box`, `plane` oder `line`.
- **Lint-Regel:** FS029 (INFO).
- **Testreferenz:** `test_fs029_std_name_collision`.

### FS030 -- addInstance mit rohen Studio-IDs
- **Symptom in Onshape:** Studio-Import scheitert oder Instanz bleibt ungeladen.
- **Ursache:** Dokument-/Element-/Versions-Strings werden statt BuildFunction/PartStudioData übergeben.
- **Lint-Regel:** FS030 (WARN), statisch erkennbare rohe Map-Form.
- **Testreferenz:** `test_fs030_addinstance_raw_ids`.

### FS031 -- Doppelte Studio-Definitionen
- **Symptom:** Studio kompiliert nicht, `featurespecs` bleibt leer, obwohl Klammern und lokale Geometrieaufrufe korrekt aussehen.
- **Ursache:** Ein Quellblock wurde doppelt eingebunden. Realer R10b-Fall: der gesamte Tray-Helfer mit zehn identischen Funktionssignaturen sowie R10B_TRAY_OUTER und R10B_TRAY_TMAX stand zweimal im Studio.
- **Lint-Regel:** FS031 (ERROR), doppelte globale Enum-/Konstanten-/Variablennamen oder identische globale Funktionssignaturen. Parameternamen und Rückgabetypen unterscheiden keine Overloads. Andere Parametertypen oder Argumentzahlen sind erlaubt; lokale gleichnamige Variablen in verschiedenen Funktionen/Blöcken werden nicht verwechselt. Beide Fundzeilen stehen im Befund. Keine Auflösung importierter Symbole.
- **Testreferenz:** `test_fs031_duplicate_studio_definitions`, `test_fs031_distinct_overloads_and_local_scopes_are_valid`, `test_fs031_duplicate_reports_both_line_numbers`.

### FS032 -- `box` als Name
- **Symptom:** Studio kompiliert nicht, `featurespecs` bleibt leer, ohne Fehlermeldung über die API.
- **Ursache:** `box` ist ein FeatureScript-Schlüsselwort (`new box(...)`). Realer Fall 2026-10-10 (Endkappen-Projekt, FS Spiegeln): `const box = evBox3d(...)`; nur das Umbenennen in `bounds` brachte die Spec zurück. FS029 deckt nur lokale Funktionen namens `box` ab.
- **Lint-Regel:** FS032 (ERROR), `const`/`var box` und Parameter `box is ...`; Strings, Kommentare und Namen wie `bbox` bleiben unberührt.
- **Testreferenz:** `test_fs032_box_as_name_flagged`, `test_fs032_box_in_other_names_strings_and_comments_is_clean`.

## JSON-Schnittstelle

`fs_lint.py --json` liefert `schema_version: 1`, `path`, `counts` mit den Schlüsseln
`ERROR`, `WARN`, `INFO`, und `findings`. Jeder Befund hat genau `rule_id`, `line`,
`severity`, `message`. `--rules --json` liefert `schema_version: 1` und `rules` mit
`id`, `severity`, `lesson`. Eingabefehler liefern zusätzlich `error.kind` und
`error.message`, aber immer eine leere `findings`-Liste. Neue Felder werden additiv
hinzugefügt, der Schema-Name bleibt stabil.


## Vertrag, Grenzen und Regressionsprüfung

- Alle Testreferenzen liegen in `pruefstand/tests/test_fs_lint.py`. Pro Regel
  sind positive und negative Fälle vorhanden; die vier Projektdateien sind
  zusätzliche lokale Integrationstests (bei fehlenden Dateien übersprungen).
- Befunde sind deterministisch nach `line`, `rule_id` sortiert. Zeilen sind
  1-basiert. `path` entspricht dem CLI-Pfad. `message` ist menschenlesbar und
  kein stabiler Parsing-Schlüssel; Integrationen verwenden `rule_id`/`severity`.
- `--rules` listet alle 31 Regeln. Seine `severity` ist die Standardstufe,
  einzelne Regeln haben dokumentierte gemischte Stufen, etwa FS001 und FS017.
- Exit 0: keine ERROR; Exit 1: nur WARN/INFO und `--strict`; Exit 2:
  ERROR oder nicht lesbare Eingabe. Ohne `--strict` blockieren WARN/INFO nicht.
- Keine vollständige AST-, Typ-, Alias-, Kontrollfluss- oder Importanalyse.
  FS002 überspringt verschachtelte Kontrollblöcke; FS019 kennt nur direkte
  literale Erzeuger; FS022 versteht direkte Parametermultiplikation;
  FS025 erkennt lexikalisches throw, nicht jeden Ausführungspfad.
- FS030 prüft nur das offensichtliche Anti-Muster roher Studio-IDs in
  addInstance. Es validiert keine externen documentId/elementId/version-Werte
  und lädt keinen Context. Gültige BuildFunction-/PartStudioData-Overloads
  brauchen nicht pauschal einen Schlüssel namens loadedContext.
- Geometriegültigkeit, echte Körperidentität, Normen berechneter Vektoren,
  dynamische Profilanzahl und tatsächliche Montage bleiben Onshape-Prüfungen.
  Ein sauberer Lint-Lauf ist keine Kompilier- oder Geometriefreigabe.
- Der Lexer speichert Positionen längentreu. Delimiterpaare, Aufrufe und
  Zeilenstarts werden gecacht; keine Newline-Zählung des gesamten Präfixes
  pro String. Ein synthetischer 258-kB-Fall ist als Regression enthalten.
