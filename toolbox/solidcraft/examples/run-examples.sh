#!/bin/zsh
# Runs every example of this folder headless on the installed SolidCraft and checks the results against the values the
# house reference states (print-handoff.md, printed-features.md, scan-to-cad.md). Run it after every SolidCraft
# update: a failure means a statement in those files no longer holds. Takes about two minutes and under 400 MB.
# Usage: toolbox/solidcraft/examples/run-examples.sh [work-dir]   (default: a new temp folder, kept for inspection)
set -u
HERE=${0:A:h}; BOX=${HERE:h:h}
WORK=${1:-$(mktemp -d /tmp/solidcraft-examples.XXXXXX)}
mkdir -p $WORK && cd $WORK || exit 2
CLI=/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli
echo "$($CLI --version), work folder $WORK"
uv run --no-project --with pillow --with ezdxf python -I $HERE/make_test_inputs.py || exit 2
uv run --no-project python -I $BOX/solidcraft/m3_hybrid_hole.py demo > m3-hybrid-hole-demo.json || exit 2
cp $HERE/*.json .
failed=0
for script in *.json(N); do
  [[ $script == *.results.json ]] && continue
  $BOX/solidcraft/sc-guard.sh run $script --results --param-check strict --json-out ${script:r}.results.json 2> ${script:r}.log
  code=$?
  # a script named refused-* documents a refusal: it has to fail
  if [[ $script == refused-* ]]; then
    (( code == 0 )) && { echo "FAIL  ${script:r}: expected a refusal, but it ran"; failed=1; }
  elif (( code != 0 )); then
    echo "FAIL  ${script:r}: $(grep -m1 '^error' ${script:r}.log)"; failed=1
  fi
done
# the laid export must survive the plate builder and slice for the A1
print -r -- "{\"out\":\"$WORK/plate.3mf\",\"bed\":[256,256],\"parts\":[{\"name\":\"Bracket\",\"stl\":\"$WORK/bracket-laid.stl\",\"at\":[128,128]}]}" > plate.spec
node $BOX/print/plate-3mf.mjs plate.spec > plate.log 2>&1 && grep -q '"height": 20' plate.log \
  && echo "ok    plate builder keeps the laid orientation (height 20)" || { echo "FAIL  plate builder"; failed=1; }
if [[ ${SLICE:-1} == 1 ]]; then      # SLICE=0 skips the slicer
  if $BOX/print/slice-a1.sh $WORK/plate.3mf > slice.log 2>&1 && grep -q "total filament weight" slice.log; then
    echo "ok    slice: $(grep -o 'model printing time.*' slice.log | tail -1)"
  else
    echo "FAIL  slice: $(tail -1 slice.log)"; failed=1
  fi
fi
uv run --no-project --with trimesh --with numpy --with networkx --with lxml python -I $HERE/check_examples.py $WORK || failed=1
uv run --no-project --with build123d python -I $HERE/check_hybrid_hole.py $WORK || failed=1
exit $failed
