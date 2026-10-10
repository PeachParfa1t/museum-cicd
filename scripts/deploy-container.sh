#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-$HOME/museum-deploy}"
IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG to the built commit tag}"
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
COMPOSE_DIR="$DEPLOY_ROOT/container"

export DEPLOY_ROOT IMAGE_TAG HOST_UID HOST_GID

mkdir -p "$COMPOSE_DIR/nginx" "$DEPLOY_ROOT/shared"
cp "$SOURCE_DIR/compose.yaml" "$COMPOSE_DIR/compose.yaml"
cp "$SOURCE_DIR/nginx/default.conf" "$COMPOSE_DIR/nginx/default.conf"

docker compose -f "$COMPOSE_DIR/compose.yaml" config --quiet

if [[ -f "$DEPLOY_ROOT/museum.pid" ]]; then
    "$SOURCE_DIR/scripts/stop.sh"
    for _attempt in 1 2 3 4 5 6 7 8 9 10; do
        if ! lsof -nP -iTCP:8081 -sTCP:LISTEN >/dev/null; then
            break
        fi
        sleep 1
    done
fi

docker compose -f "$COMPOSE_DIR/compose.yaml" pull app
docker compose -f "$COMPOSE_DIR/compose.yaml" up -d --no-build --remove-orphans
docker compose -f "$COMPOSE_DIR/compose.yaml" ps
