#!/bin/zsh
# Builds and slices every plate spec of a pack_plates.py directory, one at a time: plate-3mf.mjs, then slice-a1.sh
# (bed-only tree supports, 4 walls, 20 % infill, G-code kept for support_check.py), then support_check.py.
# Usage: slice_plates.sh plates_dir [glob]     (glob defaults to *.json, e.g. 'S2_A1-*.json')
set -u
HERE=${0:A:h}; cd $1
PATTERN=${2:-*.json}
for J in ${~PATTERN}; do
  node $HERE/plate-3mf.mjs $J > ${J:r}.plate.log 2>&1 || { echo "${J:r}: plate-3mf failed"; continue; }
  GCODE=1 PROCESS_SET='{"enable_support":"1","support_on_build_plate_only":"1","wall_loops":"4","sparse_infill_density":"20%"}' \
    $HERE/slice-a1.sh $PWD/${J:r}.3mf 2>&1 | sed "s|^|${J:r}: |"
  [[ -f ${J:r}.gcode.3mf ]] && uv run --no-project --with numpy --with scipy --with pillow python -I \
    $HERE/support_check.py $J ${J:r}.gcode.3mf > ${J:r}.support.txt 2>&1
done
echo done
