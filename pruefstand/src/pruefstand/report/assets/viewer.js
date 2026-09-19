/* Prüfstand-Bericht: Liste links, 3D rechts. Alles offline, keine Abhängigkeiten außer three.js. */
(function () {
  'use strict';
  var D = JSON.parse(document.getElementById('daten').textContent);

  // ---------------------------------------------------------------- Daten
  function b64(str, Typ) {
    var bin = atob(str), n = bin.length, bytes = new Uint8Array(n);
    for (var i = 0; i < n; i++) bytes[i] = bin.charCodeAt(i);
    return new Typ(bytes.buffer);
  }

  // Marken müssen im Durchsichtig-Durchgang zuletzt gezeichnet werden, sonst
  // übermalen sie die (ebenfalls transparenten) Kontextkörper wieder.
  var MARKE_ORDER = 1000;
  var FARBE_TEIL = 0xbfc6cd, FARBE_KONTEXT = 0x5d666f;
  var FARBE_AKTIV = 0xe4e9ee, FARBE_ROT = 0xc8503f, FARBE_GELB = 0xc9a227;

  // ------------------------------------------------------------- 3D-Szene
  var host = document.getElementById('canvas');
  var renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  host.appendChild(renderer.domElement);
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x101215);
  var camera = new THREE.PerspectiveCamera(38, 1, 0.5, 20000);
  var controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.12;

  scene.add(new THREE.AmbientLight(0xffffff, 0.55));
  var l1 = new THREE.DirectionalLight(0xffffff, 0.65); l1.position.set(1, 0.8, 1.2); scene.add(l1);
  var l2 = new THREE.DirectionalLight(0xffffff, 0.3); l2.position.set(-1, -0.6, -0.8); scene.add(l2);

  var welt = new THREE.Group();
  scene.add(welt);
  var marken = new THREE.Group();
  scene.add(marken);

  var meshes = {};
  var gesamt = new THREE.Box3();
  function positionen(k) {
    var q = b64(k.pos, Int16Array);
    var out = new Float32Array(q.length);
    for (var i = 0; i < q.length; i += 3) {
      for (var a = 0; a < 3; a++) {
        out[i + a] = k.qlo[a] + (q[i + a] + 32767) / 65534 * k.qspan[a];
      }
    }
    return out;
  }

  D.koerper.forEach(function (k) {
    var g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(positionen(k), 3));
    g.setIndex(new THREE.BufferAttribute(b64(k.idx, k.idx16 ? Uint16Array : Uint32Array), 1));
    g.computeVertexNormals();
    g.computeBoundingBox();
    var m = new THREE.MeshLambertMaterial({
      color: k.beteiligt ? FARBE_TEIL : FARBE_KONTEXT,
      transparent: !k.beteiligt, opacity: k.beteiligt ? 1.0 : 0.22,
      depthWrite: k.beteiligt, side: THREE.DoubleSide
    });
    var mesh = new THREE.Mesh(g, m);
    mesh.userData = k;
    mesh.renderOrder = k.beteiligt ? 1 : 0;
    welt.add(mesh);
    meshes[k.key] = mesh;
    gesamt.union(g.boundingBox.clone());
  });

  if (gesamt.isEmpty()) gesamt = new THREE.Box3(new THREE.Vector3(-50, -50, -50), new THREE.Vector3(50, 50, 50));
  var mitte = gesamt.getCenter(new THREE.Vector3());
  var spanne = gesamt.getSize(new THREE.Vector3()).length() || 100;
  // Z ist in diesen Modellen oben
  camera.up.set(0, 0, 1);
  camera.position.copy(mitte.clone().add(new THREE.Vector3(spanne * 0.8, -spanne * 0.9, spanne * 0.6)));
  controls.target.copy(mitte);
  camera.near = spanne / 500; camera.far = spanne * 50; camera.updateProjectionMatrix();

  function resize() {
    var w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / Math.max(h, 1);
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  if (window.ResizeObserver) new ResizeObserver(resize).observe(host);

  // ------------------------------------------------------------- Kamerafahrt
  var flug = null;
  function fliegeZu(ziel, radius) {
    // Nah genug, um die Stelle zu sehen, weit genug, um sie einordnen zu können:
    // bei winzigen Marken (ein Spalt von 1 mm) sonst Kamera im Bauteil.
    var dist = Math.min(Math.max(radius * 3.2, spanne * 0.22), spanne * 1.6);
    var richtung = camera.position.clone().sub(controls.target).normalize();
    if (!isFinite(richtung.x)) richtung.set(1, -1, 0.7).normalize();
    flug = {
      t: 0,
      vonP: camera.position.clone(), vonT: controls.target.clone(),
      nachP: ziel.clone().add(richtung.multiplyScalar(dist)), nachT: ziel.clone()
    };
  }

  function animate() {
    requestAnimationFrame(animate);
    if (flug) {
      flug.t = Math.min(1, flug.t + 0.035);
      var e = flug.t < 0.5 ? 2 * flug.t * flug.t : -1 + (4 - 2 * flug.t) * flug.t;
      camera.position.lerpVectors(flug.vonP, flug.nachP, e);
      controls.target.lerpVectors(flug.vonT, flug.nachT, e);
      if (flug.t >= 1) flug = null;
    }
    controls.update();
    renderer.render(scene, camera);
  }
  resize();
  animate();

  // ------------------------------------------------------------- Marken
  function schild(text, farbe) {
    var c = document.createElement('canvas');
    var ctx = c.getContext('2d');
    ctx.font = 'bold 44px -apple-system, Helvetica, Arial, sans-serif';
    var w = Math.ceil(ctx.measureText(text).width) + 32;
    c.width = w; c.height = 72;
    ctx = c.getContext('2d');
    ctx.fillStyle = 'rgba(16,18,21,.86)';
    ctx.fillRect(0, 0, w, 72);
    ctx.strokeStyle = farbe; ctx.lineWidth = 3; ctx.strokeRect(1.5, 1.5, w - 3, 69);
    ctx.font = 'bold 44px -apple-system, Helvetica, Arial, sans-serif';
    ctx.fillStyle = '#e8ecf0'; ctx.textBaseline = 'middle';
    ctx.fillText(text, 16, 38);
    var tex = new THREE.CanvasTexture(c);
    var sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, depthTest: false, transparent: true }));
    sp.renderOrder = MARKE_ORDER + 2;
    sp.userData.px = w / 72;
    return sp;
  }

  var schilder = [], punkte = [];
  var hoch = new THREE.Vector3();
  function skaliereMarken() {
    // Schild und Messpunkte behalten ihre Bildschirmgröße, damit ein 1-mm-Spalt
    // aus jeder Entfernung ablesbar bleibt. Das Schild sitzt über der Strecke.
    hoch.setFromMatrixColumn(camera.matrixWorld, 1).normalize();
    punkte.forEach(function (s) {
      var d = camera.position.distanceTo(s.position);
      s.scale.setScalar(Math.max(s.userData.rMin, d * 0.004));
    });
    schilder.forEach(function (sp) {
      var b = sp.userData.basis;
      var d = camera.position.distanceTo(b);
      var h = d * 0.045;
      sp.scale.set(h * sp.userData.px, h, 1);
      sp.position.copy(b).addScaledVector(hoch, h * 0.9);
    });
  }
  (function loop() { requestAnimationFrame(loop); skaliereMarken(); })();

  function leereMarken() {
    while (marken.children.length) marken.remove(marken.children[0]);
    schilder.length = 0;
    punkte.length = 0;
  }

  function punkt(p, farbe, r) {
    var s = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12),
      new THREE.MeshBasicMaterial({ color: farbe, depthTest: false, transparent: true }));
    s.position.set(p[0], p[1], p[2]);
    s.userData.rMin = r;
    s.scale.setScalar(r);
    s.renderOrder = MARKE_ORDER + 1;
    punkte.push(s);
    return s;
  }

  function strecke(a, b, farbe) {
    var g = new THREE.BufferGeometry().setFromPoints([
      new THREE.Vector3(a[0], a[1], a[2]), new THREE.Vector3(b[0], b[1], b[2])]);
    var l = new THREE.Line(g, new THREE.LineBasicMaterial({
      color: farbe, depthTest: false, transparent: true, linewidth: 2 }));
    l.renderOrder = MARKE_ORDER + 1;
    return l;
  }

  function hervorheben(keys) {
    var satz = {};
    (keys || []).forEach(function (k) { satz[k] = true; });
    welt.children.forEach(function (mesh) {
      var k = mesh.userData;
      var an = satz[k.key];
      if (k.beteiligt) {
        mesh.material.color.setHex(an ? FARBE_AKTIV : FARBE_TEIL);
        mesh.material.opacity = an ? 1.0 : (keys && keys.length ? 0.5 : 1.0);
        mesh.material.transparent = mesh.material.opacity < 1.0;
      } else {
        mesh.material.opacity = an ? 0.45 : 0.16;
      }
    });
  }

  function zeigeMarke(mess) {
    leereMarken();
    var mk = mess.marker;
    hervorheben(mess.koerper);
    if (!mk) {
      var box = new THREE.Box3();
      var treffer = false;
      (mess.koerper || []).forEach(function (k) {
        if (meshes[k]) { box.union(meshes[k].geometry.boundingBox.clone()); treffer = true; }
      });
      if (treffer) fliegeZu(box.getCenter(new THREE.Vector3()), box.getSize(new THREE.Vector3()).length() / 2);
      return;
    }
    if (mk.art === 'strecke') {
      var farbe = mk.rot ? FARBE_ROT : FARBE_GELB;
      var a = mk.a, b = mk.b;
      var mp = new THREE.Vector3((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
      var laenge = new THREE.Vector3(a[0] - b[0], a[1] - b[1], a[2] - b[2]).length();
      var r = Math.max(laenge * 0.12, spanne * 0.0025);
      marken.add(punkt(a, farbe, r));
      marken.add(punkt(b, farbe, r));
      marken.add(strecke(a, b, farbe));
      var sp = schild(mk.label, mk.rot ? '#c8503f' : '#c9a227');
      sp.userData.basis = mp.clone();
      sp.position.copy(mp);
      schilder.push(sp); marken.add(sp);
      fliegeZu(mp, Math.max(laenge, spanne * 0.01));
    } else if (mk.art === 'kaesten') {
      var alles = new THREE.Box3();
      mk.kaesten.forEach(function (kk) {
        var lo = new THREE.Vector3(kk.min[0], kk.min[1], kk.min[2]);
        var hi = new THREE.Vector3(kk.max[0], kk.max[1], kk.max[2]);
        var bb = new THREE.Box3(lo, hi);
        alles.union(bb);
        var size = bb.getSize(new THREE.Vector3());
        var g = new THREE.BoxGeometry(Math.max(size.x, 1e-3), Math.max(size.y, 1e-3), Math.max(size.z, 1e-3));
        var cube = new THREE.Mesh(g, new THREE.MeshBasicMaterial({
          color: FARBE_ROT, transparent: true, opacity: 0.3, depthTest: false
        }));
        cube.position.copy(bb.getCenter(new THREE.Vector3()));
        cube.renderOrder = MARKE_ORDER;
        marken.add(cube);
        var kante = new THREE.LineSegments(new THREE.EdgesGeometry(g),
          new THREE.LineBasicMaterial({ color: FARBE_ROT, depthTest: false, transparent: true }));
        kante.position.copy(cube.position);
        kante.renderOrder = MARKE_ORDER + 1;
        marken.add(kante);
      });
      var m = alles.getCenter(new THREE.Vector3());
      var s2 = schild(mk.label || 'Durchdringung', '#c8503f');
      s2.userData.basis = m.clone();
      s2.position.copy(m);
      schilder.push(s2); marken.add(s2);
      fliegeZu(m, alles.getSize(new THREE.Vector3()).length() / 2);
    }
  }

  // ------------------------------------------------------------- Kopf + Liste
  var k = D.kopf;
  document.querySelector('header .meta').textContent =
    [k.maschine ? 'Maschine ' + k.maschine : '', k.revision ? 'Revision ' + k.revision : '',
     k.erzeugt ? 'Lauf ' + k.erzeugt.replace('T', ' ') : '', k.tests_gesamt + ' Prüfungen']
      .filter(Boolean).join('  ·  ');

  var ampel = document.getElementById('ampel');
  D.ampel.forEach(function (a) {
    var d = document.createElement('div');
    d.className = 'zelle ' + a.outcome;
    d.innerHTML = '<span class="zahl"></span><span class="was"></span>';
    d.querySelector('.zahl').textContent = a.anzahl;
    d.querySelector('.was').textContent = a.label;
    ampel.appendChild(d);
  });

  var liste = document.getElementById('liste');
  if (D.warnungen && D.warnungen.length) {
    var wdiv = document.createElement('div');
    wdiv.id = 'warnungen';
    wdiv.textContent = 'Fehlende Geometrie: ' + D.warnungen.join(' | ');
    liste.appendChild(wdiv);
  }

  var aktiv = null;
  function waehle(el, mess) {
    if (aktiv) aktiv.classList.remove('aktiv');
    aktiv = el; el.classList.add('aktiv');
    document.getElementById('hud-titel').textContent = mess.titel;
    var txt = mess.koerper.length ? 'Körper: ' + mess.koerper.join(', ') : '';
    if (mess.hinweis) txt += (txt ? ' — ' : '') + mess.hinweis;
    document.getElementById('hud-text').textContent = txt || '—';
    zeigeMarke(mess);
  }

  D.tests.forEach(function (t) {
    var div = document.createElement('div');
    div.className = 'test ' + t.outcome;
    var kopf = document.createElement('div');
    kopf.className = 'kopf';
    kopf.innerHTML = '<span class="punkt"></span><span class="name"></span><span class="status"></span>';
    kopf.querySelector('.name').textContent = t.name;
    kopf.querySelector('.status').textContent = t.label + ' · ' + t.dauer_s.toFixed(2).replace('.', ',') + ' s';
    div.appendChild(kopf);

    var inhalt = document.createElement('div');
    inhalt.className = 'inhalt';
    if (!t.messwerte.length) {
      var leer = document.createElement('div');
      leer.className = 'leer';
      leer.textContent = 'keine Messwerte aufgezeichnet';
      inhalt.appendChild(leer);
    }
    t.messwerte.forEach(function (mess) {
      var m = document.createElement('div');
      m.className = 'mess' + (mess.schwere === 'fehler' ? ' fehler' : '')
                            + (mess.marker ? ' hat-marke' : '');
      var rows = mess.zeilen.map(function (z) {
        var td = document.createElement('td');
        td.className = 'k'; td.textContent = z[0];
        var tv = document.createElement('td');
        tv.className = 'v'; tv.textContent = z[1];
        var tr = document.createElement('tr');
        tr.appendChild(td); tr.appendChild(tv);
        return tr;
      });
      var prim = document.createElement('div'); prim.className = 'prim'; prim.textContent = mess.primitive;
      var tit = document.createElement('div'); tit.className = 'titel'; tit.textContent = mess.titel;
      m.appendChild(prim); m.appendChild(tit);
      var tab = document.createElement('table');
      rows.forEach(function (r) { tab.appendChild(r); });
      m.appendChild(tab);
      if (!mess.marker) {
        var o = document.createElement('div'); o.className = 'ohne';
        o.textContent = 'keine Stelle im Modell markierbar – die Kamera zeigt die beteiligten Körper.';
        m.appendChild(o);
      }
      if (mess.hinweis) {
        var h = document.createElement('div'); h.className = 'hinweis'; h.textContent = mess.hinweis;
        m.appendChild(h);
      }
      if (mess.png) {
        var img = document.createElement('img'); img.src = mess.png; img.alt = 'Abdeckungskarte';
        m.appendChild(img);
      }
      m.addEventListener('click', function (ev) { ev.stopPropagation(); waehle(m, mess); });
      inhalt.appendChild(m);
    });
    div.appendChild(inhalt);
    kopf.addEventListener('click', function () {
      div.classList.toggle('offen');
      if (div.classList.contains('offen')) {
        var erste = inhalt.querySelector('.mess');
        if (erste) erste.click();
        else hervorheben(t.koerper);
      }
    });
    if (t.outcome === 'failed' || t.outcome === 'error' || t.outcome === 'warnung') div.classList.add('offen');
    liste.appendChild(div);
  });

  document.getElementById('legende').textContent =
    'hell = Prüfteil und beteiligte Körper  ·  durchscheinend = Maschinenkontext (reduziert)  ·  '
    + D.koerper.length + ' Körper geladen';

  // Für Konsole/Debug greifbar machen
  window.pruefstandViewer = { scene: scene, camera: camera, controls: controls, marken: marken, meshes: meshes };

  // Beim Öffnen gleich etwas Sehenswertes zeigen: roter Befund mit Marke vor
  // rotem Befund ohne Marke vor irgendeiner Marke vor irgendeinem Messwert.
  var start = document.querySelector('.test.failed .mess.hat-marke')
           || document.querySelector('.test.failed .mess')
           || document.querySelector('.mess.fehler.hat-marke')
           || document.querySelector('.mess.hat-marke')
           || document.querySelector('.mess');
  if (start) {
    var karte = start.closest('.test');
    if (karte) karte.classList.add('offen');
    start.click();
  }
})();
