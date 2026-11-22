#!/bin/zsh
# Runs solidcraft-cli with the given arguments, kills it above LIMIT_MB resident memory (default 8 GB) and prints the
# peak. Usage: tools/sc-guard.sh run script.json --save out.sc ...
CLI=/Applications/SolidCraft.app/Contents/MacOS/solidcraft-cli
LIMIT_KB=$(( ${LIMIT_MB:-8192} * 1024 ))
$CLI "$@" &
pid=$!
peak=0
start=$(date +%s)
while kill -0 $pid 2>/dev/null; do
  rss=$(ps -o rss= -p $pid 2>/dev/null | tr -d ' ')
  rss=${rss:-0}
  (( rss > peak )) && peak=$rss
  if (( rss > LIMIT_KB )); then
    kill -9 $pid
    echo "sc-guard: KILLED at $((rss / 1024)) MB" >&2
  fi
  sleep 0.3
done
wait $pid
code=$?
echo "sc-guard: exit $code, peak $((peak / 1024)) MB, $(( $(date +%s) - start )) s" >&2
exit $code
