#!/bin/zsh
# slice-a1.sh for a Bambu Lab H3C (bed 330 x 320): the same steps and checks, see there. The result is a Bambu Studio
# project for the H3C without G-code; it is checked for the H3C bed, printer model and start G-code before it is kept.
# NOZZLE=0.2 (0.2/0.4/0.6/0.8, default 0.4) picks the H3C machine profile for that nozzle; process and filament then
# default to that machine's own defaults (0.2: 0.10mm Standard + Bambu PLA Basic @BBL H3C 0.2 nozzle), PROCESS="0.08mm
# High Quality @BBL H3C 0.2 nozzle" overrides the process.
# FILAMENT="Bambu PETG Basic @BBL H3C" picks another system filament profile (file name without .json; default PLA Basic).
# Multi-colour (AMS): FILAMENT_COLOURS="#FFFFFF;#9A2127" loads one $FILAMENT per colour (slot order = the
# "filaments" numbers in plate-3mf.mjs); optional FLUSH_VOLUMES="0,250,650,0" (row-major from -> to, mm^3).
# PROCESS_SET='{"wall_generator":"arachne"}' merges process overrides (Arachne keeps features thinner than the
# 0.5 mm first-layer line, e.g. a 0.4 mm logo ring in a colour inlay, which classic walls drop).
# Bambu Studio resets every preset key not listed in the project's different_settings_to_system to the system profile
# when it opens a project, so the PROCESS_SET keys are listed there.
# Object settings from plate-3mf.mjs ("objectSettings", e.g. supports for one part) are dropped by Bambu Studio's
# project export, so they are copied from the input's model_settings.config into the project by object name.
# ARRANGE=1 lets Bambu Studio arrange the parts (plate.json with "nested": true, positions only on the bed), rotating
# them about Z; what doesn't fit goes onto further plates of the same project, each reported below. Its packing is
# loose (2026-10-18: a 38 mm cap got a plate of its own), so outline-packed layouts are better passed as they are.
# Usage: [NOZZLE=...] [PROCESS=...] [FILAMENT=...] [FILAMENT_COLOURS=... [FLUSH_VOLUMES=...]] [PROCESS_SET=...]
#        [ARRANGE=1] [GCODE=1] tmp/print/slice-a1.sh /abs/plate.3mf
set -euo pipefail
IN=$1; BASE=${IN%.3mf}; HERE=${0:A:h}
P="/Applications/BambuStudio.app/Contents/Resources/profiles/BBL"
NOZZLE=${NOZZLE:-0.4}
W=$(mktemp -d); mkdir -p $W/out
node $HERE/resolve-bambu-profile.mjs "$P/machine/Bambu Lab H3C $NOZZLE nozzle.json" $W/machine.json >/dev/null
# The H3C picks one of the hotends in its rack per filament. The system profile leaves the rack empty and the slicer
# then stops with "No valid nozzle found" (2026-11-20), so it is filled here: RACK="Standard#9" is nine standard
# hotends, as a project saved by Bambu Studio has it. Bambu Studio sets the printer's real rack when it syncs.
RACK=${RACK:-Standard#9}
node -e 'const [f,rack]=process.argv.slice(1);const j=require(f);j.extruder_nozzle_stats=[rack];j.extruder_nozzle_count=[String(rack.split("|").reduce((n,s)=>n+Number(s.split("#")[1]),0))];require("fs").writeFileSync(f,JSON.stringify(j,null,1))' $W/machine.json "$RACK"
PROCESS=${PROCESS:-$(jq -r .default_print_profile $W/machine.json)}
FILAMENT=${FILAMENT:-$(jq -r '.default_filament_profile[0]' $W/machine.json)}
node $HERE/resolve-bambu-profile.mjs "$P/process/$PROCESS.json" $W/process.json >/dev/null
node $HERE/resolve-bambu-profile.mjs "$P/filament/$FILAMENT.json" $W/filament.json >/dev/null
node -e 'const [f,flush,set]=process.argv.slice(1);const j=Object.assign(require(f),JSON.parse(set||"{}"));j.curr_bed_type="Textured PEI Plate";if(flush)j.flush_volumes_matrix=flush.split(",");require("fs").writeFileSync(f,JSON.stringify(j,null,1))' $W/process.json "${FLUSH_VOLUMES:-}" "${PROCESS_SET:-}"
FILAMENTS=$W/filament.json
COLOURS=(${(s:;:)${FILAMENT_COLOURS:-}})
if (( ${#COLOURS} )); then
  FILES=()
  for i in {1..${#COLOURS}}; do
    node -e 'const [src,dst,c]=process.argv.slice(1);const j=require(src);j.filament_colour=[c];require("fs").writeFileSync(dst,JSON.stringify(j,null,1))' $W/filament.json $W/filament_$i.json "${COLOURS[$i]}"
    FILES+=($W/filament_$i.json)
  done
  FILAMENTS=${(j:;:)FILES}
fi
BS=/Applications/BambuStudio.app/Contents/MacOS/BambuStudio
mkdir -p $W/project
ARRANGE_ARGS=(--arrange 0)
[[ -n ${ARRANGE:-} ]] && ARRANGE_ARGS=(--arrange 1 --allow-rotations)
$BS --debug 2 $ARRANGE_ARGS --orient 0 --load-settings "$W/machine.json;$W/process.json" --load-filaments "$FILAMENTS" \
  --outputdir $W/project --export-3mf project.3mf "$IN" > $W/project-log.txt 2>&1 \
  || { echo "slice-h3c: Bambu Studio project export failed; see $W/project-log.txt" >&2; exit 1; }
if unzip -p "$IN" Metadata/model_settings.config > $W/in-model-settings.config 2>/dev/null \
  && grep -q . $W/in-model-settings.config; then
  ( cd $W/project && unzip -q -o project.3mf Metadata/model_settings.config \
    && node -e '
const fs = require("fs"); const [src, dst] = process.argv.slice(1);
const blocks = t => [...t.matchAll(/<object id="[^"]*">[\s\S]*?<\/object>/g)].map(m => m[0]);
const nameOf = b => (b.match(/<metadata key="name" value="([^"]*)"\/>/) || [])[1];
const extra = {};
for (const b of blocks(fs.readFileSync(src, "utf8"))) {
  const head = b.split("<part")[0];
  const keys = [...head.matchAll(/^\s*<metadata key="([^"]*)" value="[^"]*"\/>$/gm)].filter(m => !["name", "extruder"].includes(m[1])).map(m => m[0].trim());
  if (keys.length) extra[nameOf(b)] = keys;
}
let t = fs.readFileSync(dst, "utf8"), n = 0;
for (const b of blocks(t)) {
  const keys = extra[nameOf(b)];
  if (!keys) continue;
  const head = b.split("<part")[0];
  const fresh = keys.filter(k => !head.includes(k.split(" value=")[0]));
  t = t.replace(b, b.replace(/(<metadata key="name" value="[^"]*"\/>\n)/, `$1${fresh.map(k => "    " + k + "\n").join("")}`)); n++;
}
if (n !== Object.keys(extra).length) { console.error("slice-h3c: object settings for " + Object.keys(extra) + " matched " + n + " objects"); process.exit(1); }
fs.writeFileSync(dst, t);' $W/in-model-settings.config Metadata/model_settings.config \
    && zip -q project.3mf Metadata/model_settings.config )
fi
if [[ -n ${PROCESS_SET:-} ]]; then
  ( cd $W/project && unzip -q project.3mf Metadata/project_settings.config \
    && node -e 'const [f,set]=process.argv.slice(1);const fs=require("fs");const j=JSON.parse(fs.readFileSync(f,"utf8"));const d=j.different_settings_to_system;d[0]=[...new Set([...d[0].split(";").filter(Boolean),...Object.keys(JSON.parse(set))])].join(";");fs.writeFileSync(f,JSON.stringify(j,null,4)+"\n")' Metadata/project_settings.config "$PROCESS_SET" \
    && zip -q project.3mf Metadata/project_settings.config )
fi
$BS --debug 2 --arrange 0 --orient 0 --slice 0 --outputdir $W/out --export-3mf out.gcode.3mf $W/project/project.3mf > $W/log.txt 2>&1 \
  || { echo "slice-h3c: Bambu Studio failed to slice the project; see $W/log.txt" >&2; exit 1; }
G=$W/out/plate_1.gcode
grep -q '^; printer_model = Bambu Lab H3C$' $G && grep -q '^; printable_area = 0x0,330x0,330x320,0x320$' $G && grep -q '^; curr_bed_type = Textured PEI Plate$' $G \
  && grep -q "^; nozzle_diameter = $NOZZLE\$" $G \
  || { echo "slice-h3c: sliced G-code is not H3C/330x320/Textured PEI/$NOZZLE nozzle; see $W/log.txt" >&2; exit 1; }
grep -q "^; extruder_nozzle_stats = $RACK\$" $G || { echo "slice-h3c: hotend rack $RACK not in the sliced project; see $W/log.txt" >&2; exit 1; }
grep -q '^;===== machine: H3C start =' $G || { echo "slice-h3c: G-code lacks the Bambu H3C start G-code (include templates not resolved?); see $W/log.txt" >&2; exit 1; }
if grep -q "can not find key" $W/project-log.txt $W/log.txt; then echo "slice-h3c: unresolved profile keys; see $W/log.txt" >&2; exit 1; fi
if (( ${#COLOURS} > 1 )); then
  grep -q "^; filament_colour = ${(j:;:)COLOURS}\$" $G || { echo "slice-h3c: filament colours not applied; see $W/log.txt" >&2; exit 1; }
fi
if [[ -n ${PROCESS_SET:-} ]]; then
  node -e 'const [g,set]=process.argv.slice(1);const t=require("fs").readFileSync(g,"utf8");for(const [k,v] of Object.entries(JSON.parse(set)))if(!t.includes(`; ${k} = ${v}\n`)){console.error(`slice-h3c: ${k} = ${v} missing in the sliced project`);process.exit(1)}' $G "$PROCESS_SET"
fi
cp $W/project/project.3mf "$IN"
if [[ -n ${GCODE:-} ]]; then cp $W/out/out.gcode.3mf "$BASE.gcode.3mf"; fi
echo "$IN (Bambu project, no G-code): $(grep -m1 'model printing time' $G | sed 's/^; //'); $(grep -m1 'total filament weight' $G | sed 's/^; //'); AMS loads incl. the first: $(grep -c '^M620 S[0-9]*A' $G)"
for P in $W/out/plate_<2->.gcode(N); do
  echo "  ${P:t:r}: $(grep -m1 'model printing time' $P | sed 's/^; //'); $(grep -m1 'total filament weight' $P | sed 's/^; //')"
done
