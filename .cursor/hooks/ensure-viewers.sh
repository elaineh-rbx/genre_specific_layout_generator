#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SESSION="layoutgen-viewers"
SNAPSHOT="$ROOT/run/locked_viewers"

if tmux has-session -t "$SESSION" 2>/dev/null; then
  printf '{}\n'
  exit 0
fi

for port in 8889 8890; do
  for page in feature_viewer.html pipeline_viewer.html comparison_viewer.html; do
    if [[ ! -r "$SNAPSHOT/port-$port/$page" ]]; then
      printf '{}\n'
      exit 0
    fi
  done
done

viewer_command() {
  local port="$1"
  local snapshot="$SNAPSHOT/port-$port"
  printf '%s' \
    "while true; do " \
    "env LAYOUTGEN_FEATURE_VIEWER='$snapshot/feature_viewer.html' " \
    "LAYOUTGEN_PIPELINE_VIEWER='$snapshot/pipeline_viewer.html' " \
    "LAYOUTGEN_COMPARISON_VIEWER='$snapshot/comparison_viewer.html' " \
    "python -m layoutgen.web.server --port '$port' --home features; " \
    "sleep 1; done"
}

tmux new-session -d -s "$SESSION" -n port-8889 -c "$ROOT" \
  "$(viewer_command 8889)"
tmux new-window -d -t "$SESSION" -n port-8890 -c "$ROOT" \
  "$(viewer_command 8890)"

printf '{}\n'
