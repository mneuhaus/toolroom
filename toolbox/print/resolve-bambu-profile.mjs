// Flattens a Bambu Studio system profile (machine / process / filament JSON) by following its "inherits" chain and its
// "include" templates inside the same profile directory. Order (as Bambu and toolroom's resolve_profiles.py): inherited
// values, then includes in declared order, then the profile's own values. The Bambu Studio CLI resolves neither for
// --load-settings/--load-filaments (seen 2026-09-30: an A1 machine profile sliced with a 200 x 200 bed).
// Since Bambu Studio 2.x the A1 machine G-code routines (start, end, filament change, layer change, timelapse) live
// only in "include" templates; without them the slice silently used the generic fdm_machine_common start G-code
// (no AMS filament load, no A1 calibration), seen 2026-10-09.
// Usage: node tmp/print/resolve-bambu-profile.mjs <profile.json> <out.json>
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';

function sibling(file, name, what) {
  const path = join(dirname(file), `${name}.json`);
  if (!existsSync(path)) throw new Error(`${file}: ${what} "${name}" not found next to it`);
  return path;
}

function load(file, seen = new Set()) {
  if (seen.has(file)) throw new Error(`inherits cycle at ${file}`);
  seen.add(file);
  const { include = [], ...own } = JSON.parse(readFileSync(file, 'utf8'));
  const inherited = own.inherits ? load(sibling(file, own.inherits, 'parent profile'), seen) : {};
  const included = include.map(name => {
    const { name: _name, instantiation: _instantiation, ...values } = JSON.parse(readFileSync(sibling(file, name, 'include template'), 'utf8'));
    return values;
  });
  return Object.assign({}, inherited, ...included, own);
}

const [src, out] = process.argv.slice(2);
const flat = load(src);
delete flat.inherits;
// Keep the leaf's own 'from' (system): the CLI checks process/printer compatibility differently for user presets.
writeFileSync(out, JSON.stringify(flat, null, 1));
console.log(JSON.stringify({ out, name: flat.name, keys: Object.keys(flat).length, printable_area: flat.printable_area, printer_model: flat.printer_model }));
