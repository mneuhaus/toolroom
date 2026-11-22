# FeatureScript über UI-Injektion statt REST — Machbarkeitsrecherche

Auftrag: prüfen, ob wir FeatureScript im lokalen Electron-Bridge-Fenster über
das normale Web-Frontend (Monaco-Editor, Commit-Button) statt über REST
einspielen können, und ob das dieselben Rate-Limit-Buckets trifft.

## 1. Was die App heute kann

`~/Workspace/onshape-app/src/main.js` nutzt `webContents.executeJavaScript`
bereits an mehreren Stellen — aber nur für feste, interne Zwecke:
- `BRIDGE_SRC` installiert `window.__onshapeBridge`, das `fetch()` **innerhalb**
  des geladenen Tabs ausführt (Session-Cookie + XSRF automatisch) und die
  Antwort base64-kodiert zurückgibt. Das ist der REST-Relay-Pfad, den die MCP
  heute nutzt.
- `/_bridge/dom` liest DOM-Inventar (Inputs/Buttons/Text) rein lesend.
- `inject.js` (läuft bei jedem `dom-ready`) füllt Login-Formulare und klickt
  Reconnect-Links über native React-Value-Setter + Events.

Es gibt **keinen** öffentlichen `/_bridge/eval`- oder `/_bridge/fs-commit`-
Endpunkt, der beliebiges JS im Renderer ausführt oder den Monaco-Editor
befüllt. Die Fähigkeit dazu ist aber technisch vorhanden: `executeJavaScript`
ist Electrons Standard-API, die App instanziiert bereits beliebige
JS-Strings (siehe `folder-window.js:35`, `onshapeFolderPage.toString()`
wird als IIFE injiziert). Ein neuer Endpunkt, der einen String-Body per
`executeJavaScript` im `mainWindow` ausführt, wäre ein kleiner, klar
lokalisierter Patch in `main.js` (Muster: `/_bridge/dom`-Handler kopieren,
Body statt fester Lambda nehmen). README bestätigt explizit: „There is no
arbitrary JavaScript execution endpoint" (Stand jetzt, im Kontext der
Ordner-Werkzeuge) — das gilt für den öffentlich verdrahteten Bridge-Vertrag,
nicht für die zugrunde liegende Electron-Fähigkeit.

Kein WebSocket-Upgrade-Handling in `main.js` (`grep socket|Socket|upgrade`
→ keine Treffer). Die Bridge kann also nur HTTP relayen; einen eigenen
WS-Kanal zu Onshape müsste sie nicht selbst aufbauen — das erledigt die
bereits geladene Onshape-Webseite im `mainWindow` ohnehin selbst, sobald ein
Dokument-Tab offen ist.

## 2. Live-Check (nur lesend)

```
GET /_bridge/health  → ok, pageUrl aktuell auf der Dokumentenliste (kein offenes Element)
GET /_bridge/limits  → Bucket-Tabelle vorhanden, u.a. .../features remaining "100",
                        .../featurescript remaining "94"/"98"/"63" (mehrere Versionen v8/v9)
GET /_bridge/dom     → liefert nur die Dokumentenliste (Suchfeld, Buttons); kein
                        Feature-Studio-Tab offen, daher kein window.monaco erreichbar
                        ohne Navigation. Navigation in ein Element wäre keine
                        destruktive Aktion, wurde aber im Rahmen dieser rein
                        lesenden Recherche nicht ausgeführt.
```

Ein Monaco-Reachability-Test bräuchte einen offenen Feature-Studio-Tab; das ist
der nächste Schritt für eine echte Messung (siehe Abschnitt 5).

## 3. Wie der Onshape-Webclient tatsächlich kommuniziert

Aus dem Onshape-Blogpost „How Does Onshape Really Work?" (offizielle Quelle):

> „They communicate with the servers using both ordinary HTTPS/REST calls and
> websocket connections, using our own wire protocol."

Das bestätigt: der Webclient nutzt **zwei Kanäle** — REST für die meisten
Operationen, plus einen proprietären WebSocket-Kanal, vermutlich vor allem für
Realtime-Kollaboration (Presence, Live-Cursor, gegenseitige Sichtbarkeit von
Edits). Der Blogpost spezifiziert nicht, ob Feature-Einfügung/-Regeneration und
FeatureScript-Commits über REST oder über den WS-Kanal laufen — das bleibt
**unbelegt**. Öffentliche Onshape-Dev-Doku (`onshape-public.github.io/docs`)
beschreibt nur die REST-Ebene (Part Studios, Features, FeatureScript-Endpunkte)
als das, was Apps/Integrationen ansprechen; sie macht keine Aussage über den
internen Kanal der eigenen Web-UI.

**Praktischer Hinweis, der für „primär REST" spricht:** die App-Entwickler-Doku
(`api-adv/featureaccess`, `api-adv/partstudios`) beschreibt exakt dieselben
Microversion-/Feature-Insert-Semantiken, die auch die UI sichtbar erzeugt
(jede Änderung = eine Microversion in der History). Wenn die UI einen völlig
anderen, nicht-REST-basierten Persistenzpfad hätte, müsste der Server zwei
parallele Schreibpfade auf denselben Datenmodellen pflegen — plausibler ist,
dass der WS-Kanal für Presence/Sync/Notifications dient und die eigentlichen
State-Mutationen (Feature hinzufügen, Sketch ändern, Feature-Studio-Inhalt
speichern) weiterhin über dieselben (internen, aber REST-förmigen) Endpunkte
laufen wie die dokumentierte Public API — nur mit Session- statt API-Key-Auth.
Das ist aber eine Ableitung, keine belegte Tatsache.

## 4. Zählen UI-Aktionen auf dieselben Rate-Limit-Buckets?

Offizielle Doku (`onshape-public.github.io/docs/auth/limits/`, wörtlich
geladen und geprüft):

> „Calls that do NOT count toward API limits: […] Calls made from the Onshape
> browser, mobile clients, or the Onshape API Explorer (when authenticated via
> an Onshape session)."

**Wichtig, oft missverstanden:** Dieser Satz steht im Abschnitt „Annual API
Call Limits" (das jährliche `keyCount`-Kontingent, 402 bei Überschreitung) —
**nicht** im Abschnitt „Rate Limits" (die Pro-Endpunkt-429-Fenster mit
`X-Rate-Limit-Remaining`, das, was `/_bridge/limits` misst). Die Doku trennt
beide Mechanismen explizit und macht zur Session-Ausnahme nur für das
Jahres-Kontingent eine Aussage. Zu den Pro-Endpunkt-Rate-Limits sagt die Doku
nichts über eine Session-Ausnahme.

**Eigene Messung widerspricht der optimistischen Lesart ohnehin:** Der
Session-Bridge-Traffic selbst (Fetch mit Cookie+XSRF aus dem `mainWindow`,
technisch ununterscheidbar von echtem UI-Traffic) zeigt in `/_bridge/limits`
exakt die dokumentierten knappen Buckets: `.../features` bei 100,
`.../featurescript` bei 94/98/63 je nach API-Version. Das ist derselbe
Mechanismus, den man vermeiden möchte. Da die Bridge-Calls und potenzielle
UI-Klicks beide session-authentifizierte Same-Origin-Fetches gegen dieselben
Server-Routen sind, gibt es keinen erkennbaren Grund, warum der Server
zwischen „von Code ausgelöster fetch()" und „von einem Nutzerklick
ausgelöster fetch()" unterscheiden sollte — beide erzeugen identische HTTP-
Requests. Die Rate-Limit-Zählung sitzt vermutlich auf dem API-Gateway/Service
pro Konto+Endpunkt, unabhängig vom Auslöser im Client.

**Schlussfolgerung (mit Unsicherheit markiert):**
- Belegt: Jahres-Metering (`keyCount`) ignoriert Session-Auth-Calls — das
  nutzt die Bridge bereits aus, das ist der ganze Sinn der heutigen Architektur.
- Belegt durch eigene Messung: die Pro-Endpunkt-429-Buckets (100/100/500/3000…)
  greifen auch bei Session-Auth-Calls über die Bridge.
- Unbelegt, aber plausibel: dieselben Buckets greifen auch, wenn genau dieselbe
  REST-Anfrage stattdessen durch einen echten Klick in der UI ausgelöst wird
  (Monaco-Commit, Feature-Dialog-OK) — weil es serverseitig dieselbe Anfrage
  ist. Eine UI-Injektion würde also mit hoher Wahrscheinlichkeit **kein**
  zusätzliches Kontingent freischalten, sondern nur denselben Bucket über einen
  unzuverlässigeren, fehleranfälligeren Weg verbrauchen.
- Unbelegt und ungeprüft: ob FeatureScript-Commit aus dem Feature-Studio-Editor
  einen anderen internen Endpunkt/Pfad nutzt als der öffentliche
  `POST .../featurestudios/d/{d}/w/{w}/e/{e}` (Contents), der bereits von der
  Bridge genutzt wird und im 3000er „Writes"-Bucket landet, nicht im knappen
  100er FS-Eval-Bucket. Falls ja, wäre der Umweg über die UI für
  Feature-Studio-Bearbeitung ohnehin unnötig — der REST-Weg dafür ist schon
  der großzügige Bucket, nicht der 100er.

## 5. Vorschlag für einen konkreten Bridge-Endpunkt

Falls das Experiment (Abschnitt 6) die Hypothese widerlegt und UI-Injektion
tatsächlich einen anderen/größeren Bucket träfe, wäre der Endpunkt:

```
POST /_bridge/fs-commit
Body: { documentId, workspaceId, elementId, source: "<FeatureScript-Text>" }
```

Implementierung (Skizze, Muster wie `/_bridge/dom`):
1. Sicherstellen, dass der `mainWindow`-Tab bereits auf dem passenden
   Feature-Studio-Element steht (sonst vorher navigieren/warten).
2. `executeJavaScript` mit einer IIFE, die:
   - `window.monaco`/den Editor-Instanz-Handle sucht (Selector- oder
     Modell-basiert, z. B. über `monaco.editor.getModels()` oder das
     Onshape-eigene Editor-Wrapper-Objekt, falls exponiert),
   - den Inhalt per Editor-API setzt (nicht per rohem `element.value`, da
     Monaco eine Canvas/CodeMirror-artige Eigen-Rendering hat — direktes
     DOM-Value-Setzen funktioniert bei Monaco nicht, es braucht die
     Editor-API `model.setValue(...)`),
   - den „Commit"/„Save"-Button klickt oder das äquivalente Tastenkürzel
     simuliert (Cmd/Ctrl+S ist in Onshape möglicherweise gemappt).
3. Warten auf ein Erfolgssignal (DOM-Text „gespeichert"/Fehleranzeige, oder
   Polling auf einen internen Store) — es gibt **keine** direkte
   Regenerations-Antwort wie bei REST (`featureStatus`, `notices`); Erfolg
   müsste über UI-Zustand/Notification-Toasts erschlossen werden.
4. Rückgabe: bestenfalls `{ok, committed: bool, detail}`, ehrlich mit
   Unsicherheit (kein serverseitiger Response-Body verfügbar).

## 6. Risiken

- **Kein strukturiertes Ergebnis.** REST liefert `featureStatus`/`notices`
  direkt; UI-Injektion liefert nur DOM-Text/Toasts — fehleranfällige
  Heuristik, schwerer zu automatisieren und zu verifizieren als der
  bestehende REST-Weg.
- **Fragile Selektoren.** Monaco-Interna und Onshape-UI-Struktur können sich
  jederzeit ändern (wie bereits beim zweistufigen Login gesehen); ein
  UI-Injection-Pfad bricht öfter als stabile REST-Endpunkte.
- **Session-/Fokus-Konflikte.** `inject.js` demonstriert bereits, wie heikel
  Fokus-Handling in diesem Setup ist (Secure-Input-Problem bei Passwortfeldern).
  Ein automatisierter Tastatur-/Klick-Flow im selben sichtbaren Fenster kann
  mit anderen laufenden Aktionen (z. B. gleichzeitige MCP-Bridge-Calls)
  kollidieren, da beide denselben `mainWindow`-Tab teilen.
- **Kein Geschwindigkeitsvorteil zu erwarten**, wenn Abschnitt 4 zutrifft —
  dann ist der Aufwand für Fragilität ohne Kontingent-Gewinn eingetauscht.
- **ToS-Grauzone wird nicht kleiner.** Die Bridge nutzt bereits die Session;
  ein UI-Simulationspfad ist keine sauberere Interpretation der Nutzungs-
  bedingungen als der jetzige REST-Relay — eher unklarer, weil er UI-
  Interaktion vortäuscht statt sie transparent als API-Zugriff zu behandeln.

## 7. Nötige Messung, um die Hypothese wirklich zu klären

1. Feature-Studio-Tab öffnen (Navigation, keine Schreiboperation).
2. `curl .../_bridge/limits` → aktuellen Stand von
   `.../featurescript` und `.../featurestudios/.../e/*` (Contents) notieren.
3. **Manuell** (Marc selbst, echte Maus/Tastatur, nicht die Bridge) im
   Feature-Studio-Editor einen trivialen Kommentar hinzufügen und speichern.
4. `curl .../_bridge/limits` erneut → prüfen, ob sich `remaining` für
   `.../featurestudios/.../e/*` (den 3000er Contents-Bucket) oder für einen
   bisher ungesehenen Pfad ändert, und ob sich der 100er FS-Eval-Bucket
   NICHT bewegt (Vorhersage: Speichern verbraucht den 3000er Bucket, nicht
   den 100er — das wäre bereits heute über REST günstiger erreichbar).
5. Für die schärfere Frage („trifft UI-Regenerierung den knappen
   `.../features`-100er-Bucket oder etwas anderes?"): einen Feature per Klick
   im Feature-Baum umbenennen/neu berechnen lassen und denselben Vorher-
   Nachher-Vergleich fahren.

Dieses Experiment wurde in diesem Auftrag **nicht** durchgeführt (erfordert
manuelle UI-Interaktion durch Marc, kein Bridge-Call) und ist der einzige
Weg, Abschnitt 4 von „plausibel" zu „belegt" zu heben.

---

## Kurzfassung (für Marc)

- Technisch möglich: ja. `executeJavaScript` kann beliebiges JS im geladenen
  Onshape-Tab ausführen (die App macht das schon für Login/DOM-Lesen); ein
  `/_bridge/fs-commit`-Endpunkt, der Monaco befüllt und Commit klickt, wäre
  ein kleiner, klar lokalisierter Patch — es gibt heute aber noch keinen.
- Kein separater WS-Umgehungspfad in der Bridge: `main.js` hat kein
  WebSocket-Handling; der offene `mainWindow`-Tab nutzt aber ohnehin Onshapes
  eigenen WS-Kanal, sobald ein Dokument offen ist.
- Offizielle Doku bestätigt nur, dass Session-Calls vom **Jahres-Metering**
  (`keyCount`) ausgenommen sind — das nutzt die Bridge bereits.
- Zu den **Pro-Endpunkt-Rate-Limit-Buckets** (die knappen 100er, die wehtun)
  macht die Doku keine Session-Ausnahme. Eigene Messungen zeigen: dieselben
  Buckets greifen bei session-authentifizierten Bridge-Calls genauso wie bei
  API-Key-Calls. Da UI-Klicks serverseitig dieselben Requests erzeugen, ist
  ein Kontingent-Vorteil durch UI-Injektion **unbelegt und unwahrscheinlich**.
- Falls FeatureScript-Speichern über die UI denselben `contents`-Endpunkt
  trifft wie heute die Bridge, landet das ohnehin im großzügigen 3000er
  Writes-Bucket, nicht im knappen 100er FS-Eval-Bucket — das spricht dafür,
  dass der bestehende REST-Weg für Feature-Studio-Edits schon der günstige
  Weg ist, und UI-Injektion nichts gewinnt außer mehr Fragilität.
- Nötige Messung, um das sicher zu wissen: einmal manuell (echte Maus/
  Tastatur, nicht die Bridge) im Feature-Studio speichern/regenerieren und
  `x-rate-limit-remaining` vorher/nachher über `/_bridge/limits` vergleichen.
  Das wurde in dieser Recherche nicht gemacht (erfordert Marcs manuelle
  Interaktion).
- Empfehlung: kein Bau des `/_bridge/fs-commit`-Endpunkts, bevor diese eine
  manuelle Messung vorliegt — sonst wird Aufwand in einen Pfad investiert,
  der wahrscheinlich keinen Kontingent-Vorteil bringt und zusätzlich fragiler
  ist als der bestehende REST-Relay.
