#!/bin/bash
# Render a feeder clip replayed from a physics log (sim.clip in sorter-v2-sim) in one look, then
# encode it on white at 30 fps.
#   clip.sh LOOK SIMCLIP OUT [--limit N]    LOOK: photo (Cycles) or cad (Workbench, Onshape's look)
set -euo pipefail
LOOK=${1:?photo or cad}; TRAJ=${2:?sim clip dir}; OUT=${3:?out dir}; shift 3
R=$HOME/renders/sorter-v2
$HOME/blender/blender-5.2.1-linux-x64/blender -b --python $R/code/sorter_render.py -- \
  --gltf $R/sorter_medium.gltf --out "$OUT" --stage clip --traj "$TRAJ" --look "$LOOK" \
  --ldraw $HOME/renders/ldraw "$@"
IFS=x read W H < <(ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=s=x:p=0 "$OUT/frames/clip_0001.png")
ffmpeg -loglevel error -y -f lavfi -i "color=c=white:s=${W}x${H}:r=30" -framerate 30 -i "$OUT/frames/clip_%04d.png" \
  -filter_complex "[0][1]overlay=shortest=1,format=yuv420p" -c:v libx264 -crf 18 "$OUT/clip_$LOOK.mp4"
echo "STEP done $OUT/clip_$LOOK.mp4"
