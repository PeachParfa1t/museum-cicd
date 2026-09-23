#!/usr/bin/env bash

set -Eeuo pipefail

DEPLOY_ROOT="${DEPLOY_ROOT:-$HOME/museum-deploy}"
PID_FILE="$DEPLOY_ROOT/museum.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "PID-файл не найден. Сайт уже остановлен или ещё не разворачивался."
    exit 0
fi

PID="$(tr -cd '0-9' < "$PID_FILE")"

if [[ -n "$PID" ]] && kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    echo "Сайт остановлен. PID: $PID"
else
    echo "Процесс с PID $PID не найден."
fi

rm -f "$PID_FILE"
