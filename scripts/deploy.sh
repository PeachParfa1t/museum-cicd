#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-$HOME/museum-deploy}"
RELEASES_DIR="$DEPLOY_ROOT/releases"
SHARED_DIR="$DEPLOY_ROOT/shared"
VENV_DIR="$DEPLOY_ROOT/venv"
CURRENT_LINK="$DEPLOY_ROOT/current"
PID_FILE="$DEPLOY_ROOT/museum.pid"
LOG_FILE="$DEPLOY_ROOT/museum.log"
DATABASE_FILE="$SHARED_DIR/museum.db"
APP_PORT="${APP_PORT:-8081}"
RELEASE_NAME="${BUILD_NUMBER:-manual-$(date +%Y%m%d%H%M%S)}"
RELEASE_DIR="$RELEASES_DIR/$RELEASE_NAME"

echo "Подготовка каталога развёртывания: $DEPLOY_ROOT"
mkdir -p "$RELEASES_DIR" "$SHARED_DIR" "$RELEASE_DIR"

echo "Копирование версии $RELEASE_NAME"
rsync -a \
    --exclude ".git/" \
    --exclude ".venv/" \
    --exclude ".pytest_cache/" \
    --exclude "__pycache__/" \
    --exclude "instance/*.db" \
    --exclude "build/" \
    --exclude "test-results.xml" \
    "$SOURCE_DIR/" "$RELEASE_DIR/"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    echo "Создание production-окружения Python"
    python3 -m venv "$VENV_DIR"
fi

echo "Установка production-зависимостей"
"$VENV_DIR/bin/python" -m pip install --upgrade pip
"$VENV_DIR/bin/python" -m pip install -r "$RELEASE_DIR/requirements.txt"

if [[ -f "$PID_FILE" ]]; then
    OLD_PID="$(tr -cd '0-9' < "$PID_FILE")"

    if [[ -n "$OLD_PID" ]] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "Остановка предыдущей версии с PID $OLD_PID"
        kill "$OLD_PID"

        for _attempt in 1 2 3 4 5 6 7 8 9 10; do
            if ! kill -0 "$OLD_PID" 2>/dev/null; then
                break
            fi
            sleep 1
        done

        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Предыдущая версия не остановилась за 10 секунд"
            exit 1
        fi
    fi
fi

ln -sfn "$RELEASE_DIR" "$CURRENT_LINK"

echo "Запуск новой версии на порту $APP_PORT"
cd "$CURRENT_LINK"
JENKINS_NODE_COOKIE="museum-archive-service" \
DATABASE_PATH="$DATABASE_FILE" \
nohup "$VENV_DIR/bin/waitress-serve" \
    --host=127.0.0.1 \
    --port="$APP_PORT" \
    wsgi:app >> "$LOG_FILE" 2>&1 < /dev/null &

NEW_PID=$!
echo "$NEW_PID" > "$PID_FILE"

echo "Запущена версия $RELEASE_NAME с PID $NEW_PID"
echo "Лог: $LOG_FILE"
