// Builds a ready-to-slice 3MF build plate (Bambu Lab A1: 256 x 256 mm) from STL parts exported by the CAD backend.
// Each part gets a print orientation (rotations in 90-degree steps, exact; about z any angle), is dropped onto the bed (min z = 0) and
// placed at a plate position; the transforms are baked into the mesh. The meshes stay the CAD export's own
// tessellation; this tool only moves them rigidly, it never re-tessellates.
// Usage: node plate-3mf.mjs <plate.json>
//   plate.json: { "out": "/abs/plate.3mf", "bed": [256, 256], "parts": [ { "name", "stl": "/abs/part.stl",
//                 "rotate": [["x", -90], ["z", 90]], "at": [x, y] (centre of the part's footprint on the bed) } ] }
//   "nested": true skips the bounding-box spacing check, for layouts packed by their outlines elsewhere or arranged by
//   the slicer (slice-a1.sh ARRANGE=1).
//   "stl" may be a list: the pieces keep their relative placement and become the parts (3MF components) of one
//   object, which the slicer joins (for bodies the mesher can only tessellate piece by piece).
//   Multi-colour: "filaments": [1, 2] (one AMS slot per piece of the "stl" list) and optional "pieceNames" write a
//   Bambu Metadata/model_settings.config that assigns each piece (3MF part) its filament; optional "pieceSettings"
//   (one object of Bambu process keys per piece, e.g. {"sparse_infill_density": "100%"}) become that part's own settings.
//   "objectSettings": Bambu process keys for the whole object, for keys Bambu only takes per object, e.g. supports for
//   one part of the plate: {"enable_support": "1", "support_type": "tree(auto)", "support_on_build_plate_only": "1"}
//   (2026-11-04: as part settings Bambu ignored them).
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';

const spec = JSON.parse(readFileSync(resolve(process.argv[2]), 'utf8'));
const [bedX, bedY] = spec.bed ?? [256, 256];

function readStl(file) {
  const buf = readFileSync(file);
  const count = buf.readUInt32LE(80);
  if (buf.length !== 84 + 50 * count) throw new Error(`${file}: not a binary STL (size ${buf.length}, ${count} triangles)`);
  const tris = [];
  for (let i = 0; i < count; i++) {
    const o = 84 + 50 * i + 12;
    tris.push([0, 1, 2].map(k => [0, 1, 2].map(c => buf.readFloatLE(o + 12 * k + 4 * c))));
  }
  return tris;
}

// Exact quarter-turn rotations: coordinates are only permuted and negated. About z (the bed's normal) any other angle
// is allowed too, to lay a part diagonally on the bed: that turn is computed (cos, sin) and leaves z as it is.
function rotate(p, axis, degrees) {
  const turns = ((Math.round(degrees / 90) % 4) + 4) % 4;
  if (Math.abs(degrees / 90 - Math.round(degrees / 90)) > 1e-12) {
    if (axis !== 'z') throw new Error(`rotation ${degrees} about ${axis} is not a multiple of 90 degrees (only z may be turned freely)`);
    const a = degrees * Math.PI / 180, c = Math.cos(a), s = Math.sin(a);
    return [p[0] * c - p[1] * s, p[0] * s + p[1] * c, p[2]];
  }
  let [x, y, z] = p;
  for (let t = 0; t < turns; t++) {
    if (axis === 'x') [y, z] = [-z, y];
    else if (axis === 'y') [x, z] = [z, -x];
    else if (axis === 'z') [x, y] = [-y, x];
    else throw new Error(`axis ${axis}`);
  }
  return [x, y, z];
}

const objects = [];
const report = [];
for (const [index, part] of spec.parts.entries()) {
  const pieces = [part.stl].flat().map(file => readStl(file).map(t => t.map(p => (part.rotate ?? []).reduce((q, [axis, deg]) => rotate(q, axis, deg), p))));
  const tris = pieces.flat();
  // A reduce, not Math.min(...spread): a spread of ~200k coordinates overflows the call stack (2026-10-03).
  const min = [0, 1, 2].map(c => tris.flat().reduce((m, p) => Math.min(m, p[c]), Infinity));
  const max = [0, 1, 2].map(c => tris.flat().reduce((m, p) => Math.max(m, p[c]), -Infinity));
  const shift = [part.at[0] - (min[0] + max[0]) / 2, part.at[1] - (min[1] + max[1]) / 2, -min[2]];
  const moved = pieces.map(piece => piece.map(t => t.map(p => p.map((v, c) => v + shift[c]))));
  const lo = [min[0] + shift[0], min[1] + shift[1], 0];
  const hi = [max[0] + shift[0], max[1] + shift[1], max[2] - min[2]];
  if (lo[0] < 0 || lo[1] < 0 || hi[0] > bedX || hi[1] > bedY) throw new Error(`${part.name} leaves the ${bedX} x ${bedY} bed: ${lo} .. ${hi}`);
  // Index each piece's triangle soup; identical coordinates become one vertex (each STL is watertight by construction).
  const meshes = moved.map(piece => {
    const ids = new Map(), vertices = [], triangles = [];
    for (const t of piece) {
      triangles.push(t.map(p => {
        const key = p.map(v => v.toFixed(6)).join(',');
        if (!ids.has(key)) { ids.set(key, vertices.length); vertices.push(p); }
        return ids.get(key);
      }));
    }
    return { vertices, triangles };
  });
  if (part.filaments && part.filaments.length !== meshes.length) throw new Error(`${part.name}: ${part.filaments.length} filaments for ${meshes.length} pieces`);
  objects.push({ name: part.name, meshes, filaments: part.filaments, pieceNames: part.pieceNames, pieceSettings: part.pieceSettings, objectSettings: part.objectSettings });
  report.push({ name: part.name, pieces: meshes.length, triangles: meshes.reduce((n, m) => n + m.triangles.length, 0), footprint: [hi[0] - lo[0], hi[1] - lo[1]].map(v => +v.toFixed(2)), height: +hi[2].toFixed(2), at: part.at });
}
// Footprint boxes must not overlap (5 mm gap), unless "nested": true (outline-packed or slicer-arranged layouts).
for (let i = 0; i < report.length && !spec.nested; i++) for (let j = i + 1; j < report.length; j++) {
  const [a, b] = [report[i], report[j]];
  const apart = [0, 1].some(c => Math.abs(a.at[c] - b.at[c]) >= (a.footprint[c] + b.footprint[c]) / 2 + 5);
  if (!apart) throw new Error(`${a.name} and ${b.name} are closer than 5 mm on the bed`);
}

// 3MF resources: every mesh is an object; a part made of several pieces is an extra object with components.
let nextId = 1;
const resources = [], items = [], settings = [];
for (const o of objects) {
  const pieceName = i => o.pieceNames?.[i] ?? (o.meshes.length > 1 ? `${o.name} (piece ${i + 1})` : o.name);
  const ids = o.meshes.map((m, i) => { const id = nextId++; resources.push({ id, name: pieceName(i), mesh: m }); return id; });
  if (ids.length === 1 && !o.filaments && !o.objectSettings) { items.push(ids[0]); continue; }
  const id = nextId++; resources.push({ id, name: o.name, components: ids }); items.push(id);
  if (o.filaments || o.objectSettings) settings.push({ id, name: o.name, extra: o.objectSettings ?? {}, parts: ids.map((pid, i) => ({ id: pid, name: pieceName(i), filament: o.filaments?.[i] ?? 1, extra: o.pieceSettings?.[i] ?? {} })) });
}
const esc = s => String(s).replace(/[<>&"]/g, c => ({ '<': '&lt;', '>': '&gt;', '&': '&amp;', '"': '&quot;' }[c]));
const model = `<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">
 <metadata name="Title">${esc(spec.title ?? 'build plate')}</metadata>
 <metadata name="Application">Toolroom plate-3mf</metadata>
 <resources>
${resources.map(r => r.components ? `  <object id="${r.id}" name="${esc(r.name)}" type="model">
   <components>
${r.components.map(c => `    <component objectid="${c}"/>`).join('\n')}
   </components>
  </object>` : `  <object id="${r.id}" name="${esc(r.name)}" type="model">
   <mesh>
    <vertices>
${r.mesh.vertices.map(v => `     <vertex x="${v[0].toFixed(6)}" y="${v[1].toFixed(6)}" z="${v[2].toFixed(6)}"/>`).join('\n')}
    </vertices>
    <triangles>
${r.mesh.triangles.map(t => `     <triangle v1="${t[0]}" v2="${t[1]}" v3="${t[2]}"/>`).join('\n')}
    </triangles>
   </mesh>
  </object>`).join('\n')}
 </resources>
 <build>
${items.map(id => `  <item objectid="${id}"/>`).join('\n')}
 </build>
</model>
`;
const dir = mkdtempSync(join(tmpdir(), 'plate3mf-'));
mkdirSync(join(dir, '3D')); mkdirSync(join(dir, '_rels'));
writeFileSync(join(dir, '[Content_Types].xml'), `<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
 <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
 <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>
</Types>
`);
writeFileSync(join(dir, '_rels', '.rels'), `<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
 <Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>
</Relationships>
`);
writeFileSync(join(dir, '3D', '3dmodel.model'), model);
// Bambu's per-object/per-part settings: object id = the component object, part id = the piece's mesh object.
if (settings.length) {
  mkdirSync(join(dir, 'Metadata'));
  writeFileSync(join(dir, 'Metadata', 'model_settings.config'), `<?xml version="1.0" encoding="UTF-8"?>
<config>
${settings.map(o => `  <object id="${o.id}">
    <metadata key="name" value="${esc(o.name)}"/>
    <metadata key="extruder" value="${o.parts[0].filament}"/>
${Object.entries(o.extra).map(([k, v]) => `    <metadata key="${esc(k)}" value="${esc(v)}"/>\n`).join("")}${o.parts.map(p => `    <part id="${p.id}" subtype="normal_part">
      <metadata key="name" value="${esc(p.name)}"/>
      <metadata key="extruder" value="${p.filament}"/>
${Object.entries(p.extra).map(([k, v]) => `      <metadata key="${esc(k)}" value="${esc(v)}"/>\n`).join("")}    </part>`).join('\n')}
  </object>`).join('\n')}
</config>
`);
}
const out = resolve(spec.out);
mkdirSync(dirname(out), { recursive: true });
rmSync(out, { force: true });
execFileSync('zip', ['-q', '-X', '-r', out, '[Content_Types].xml', '_rels', '3D', ...(settings.length ? ['Metadata'] : [])], { cwd: dir });
rmSync(dir, { recursive: true, force: true });
console.log(JSON.stringify({ out, bed: [bedX, bedY], parts: report }, null, 1));
