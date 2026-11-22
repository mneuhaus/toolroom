#!/bin/zsh
# Shows that every kind of hint appears on a design built to trigger it, and that a plain sound part gets none.
# Usage: toolbox/check/selftest.sh
set -u
HERE=${0:A:h}; WORK=$(mktemp -d /tmp/toolroom-check-selftest.XXXXXX); cd $WORK
CLI=/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli
box() { # body, length, width, height, corner, operation (new | join | cut), feature name
  local op=${6:-new} target=""
  [[ $op == new ]] && target="\"body_name\":\"$1\"" || target="\"targets\":[\"$1\"]"
  print -r -- "{\"command\":\"solid.box\",\"params\":{\"length\":\"$2 mm\",\"width\":\"$3 mm\",\"height\":\"$4 mm\",\"corner\":[$5],\"operation\":\"$op\",$target,\"name\":\"$1 ${7:-block}\"}}"
}
print -r -- "{\"commands\":[
 $(box Fin 30 20 4 0,0,0), $(box Fin 20 0.6 10 5,10,4 join fin),
 $(box Slotted 20 20 10 0,40,0), $(box Slotted 0.3 20 8 10,40,2 cut slot),
 $(box A 10 10 10 50,0,0), $(box B 10 10 10 55,5,5),
 $(box C 10 10 10 50,40,0), $(box D 10 10 10 60.08,40,0),
 $(box Long 300 10 10 0,80,0)]}" > faulty.json
print -r -- "{\"commands\":[ $(box Sound 30 20 10 0,0,0),
 {\"command\":\"solid.cylinder\",\"params\":{\"diameter\":\"5 mm\",\"height\":\"10 mm\",\"base\":[15,10,0],\"operation\":\"cut\",\"targets\":[\"Sound\"],\"name\":\"Bore\"}},
 {\"command\":\"body.print_face\",\"params\":{\"body\":\"Sound\",\"point\":[5,5,0]}}]}" > sound.json
failed=0
for name in faulty sound; do
  $CLI run $name.json --save $name.sc > /dev/null 2> $name.log || { echo "FAIL  could not build $name: $(tail -1 $name.log)"; exit 1; }
  $HERE/check $name.sc --json $name.hints.json > $name.txt 2>&1
done
expect() { # kind, body pattern
  if jq -e --arg k "$1" --arg b "$2" '[.hints[] | select(.kind == $k and (.body | test($b)))] | length > 0' faulty.hints.json > /dev/null
  then echo "ok    $1 on $2"; else echo "FAIL  no $1 hint on $2"; failed=1; fi
}
expect thin Fin; expect gap Slotted; expect overlap "A / B"; expect gap "C / D"; expect bed Long; expect "print face" Fin
n=$(jq '.hints | length' sound.hints.json)
[[ $n == 0 ]] && echo "ok    a sound part gets no hints" || { echo "FAIL  the sound part got $n hints:"; jq -r '.hints[] | "      \(.kind) \(.text)"' sound.hints.json; failed=1; }
echo "work folder: $WORK"
exit $failed
