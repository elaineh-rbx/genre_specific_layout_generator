#!/usr/bin/env bash
# Keep the playground (8887) and the viewers (8888) up.
#
# Both ports run the same program: one opens on the playground, the other on the
# viewer index, and every other path is identical on both. Each gets a detached
# supervisor loop that restarts it if it ever exits, so a crash costs five seconds
# instead of staying down until someone notices.
#
# A supervisor cannot survive the container itself going away, so ~/.zshrc calls this
# script too: opening any shell brings the pair back. Running it is always safe - a
# port already being served is left alone.
#
#   serve.sh            start whatever is not already up
#   serve.sh restart    reload both with the current code
#   serve.sh stop       stop the servers and their supervisors
#   serve.sh status     what is up, and what each port answers

set -u

REPO=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
PY="${LAYOUTGEN_PYTHON:-$(command -v python3)}"
LOGS="$REPO/run/logs"
PORTS=(8887 8888)
HOMES=(playground viewers)
TAG=layoutgen-serve           # appears in each supervisor's command line, so they can be
                         # found again without a pid file to go stale

bound()    { ss -tln 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${1}\$"; }
healthy()  { curl -fs -o /dev/null --max-time 5 "http://127.0.0.1:${1}/api/health"; }
watching() { pgrep -f "$TAG watching :${1}\b" >/dev/null 2>&1; }

# The server holding a port, so a wedged one can be replaced on its own.
pid_on() {
    ss -tlnp 2>/dev/null | awk -v p="[:.]${1}\$" '$4 ~ p' \
        | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | head -1
}

supervise() {
    local port=$1 home=$2 log="$LOGS/${port}.log"
    mkdir -p "$LOGS"
    setsid bash -c '
        cd "'"$REPO"'"
        while true; do
            echo "[$(date -Is)] '"$TAG"' watching :'"$port"' ('"$home"')" >> "'"$log"'"
            "'"$PY"'" -m layoutgen.web.server --port '"$port"' --home '"$home"' >> "'"$log"'" 2>&1
            echo "[$(date -Is)] :'"$port"' exited $?, restarting in 5s" >> "'"$log"'"
            sleep 5
        done
    ' </dev/null >/dev/null 2>&1 &
    disown $! 2>/dev/null || true
}

start_one() {
    local port=$1 home=$2 pid waited=0
    local lock="/tmp/${TAG}-${port}.lock"
    if watching "$port"; then
        echo "  :$port already supervised"
        return 0
    fi
    if bound "$port"; then
        if healthy "$port"; then
            # Someone started this by hand. Leave it, but say so - it will not come
            # back on its own if it dies.
            echo "  :$port up but unsupervised (serve.sh restart to adopt it)"
            return 0
        fi
        echo "  :$port bound but not answering - replacing it"
        pid=$(pid_on "$port")
        [ -n "$pid" ] && kill "$pid" 2>/dev/null
        sleep 2
    fi
    # One starter at a time, and the lock is held until the port is actually bound:
    # a second shell arriving mid-startup would otherwise see a free port and raise
    # a rival supervisor that can never bind. The waiting happens in the background
    # so that opening a terminal is never delayed by a server starting up.
    mkdir "$lock" 2>/dev/null || return 0
    supervise "$port" "$home"
    (
        while [ $waited -lt 25 ] && ! bound "$port"; do
            sleep 1
            waited=$((waited + 1))
        done
        rmdir "$lock" 2>/dev/null
    ) </dev/null >/dev/null 2>&1 &
    disown $! 2>/dev/null || true
    echo "  :$port starting ($home)"
}

stop_all() {
    pkill -f "$TAG watching" 2>/dev/null
    # Matches the module path loosely, so a server started before the package was
    # reorganised is still adopted rather than left holding the port.
    pkill -f "layoutgen[.a-z]*server --port" 2>/dev/null
    sleep 1
    rmdir /tmp/${TAG}-*.lock 2>/dev/null
    return 0
}

status() {
    local i port who
    for i in "${!PORTS[@]}"; do
        port=${PORTS[$i]}
        if healthy "$port"; then
            watching "$port" && who="supervised" || who="NOT supervised"
            echo "  :$port up (${HOMES[$i]}) - $who"
        elif bound "$port"; then
            echo "  :$port bound but not answering"
        else
            echo "  :$port down"
        fi
    done
}

start_all() {
    local i
    for i in "${!PORTS[@]}"; do start_one "${PORTS[$i]}" "${HOMES[$i]}"; done
}

# Only for the commands run by hand: an automatic start never waits.
wait_up() {
    local i=0
    while [ $i -lt 30 ]; do
        healthy "${PORTS[0]}" && healthy "${PORTS[1]}" && return 0
        sleep 1
        i=$((i + 1))
    done
    return 1
}

case "${1:-start}" in
    stop)    stop_all; echo "stopped" ;;
    restart) stop_all; start_all; wait_up; status ;;
    status)  status ;;
    *)       start_all ;;
esac
