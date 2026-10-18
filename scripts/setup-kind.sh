#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_ROOT="${DEPLOY_ROOT:-$HOME/museum-deploy}"
CLUSTER_NAME=museum-lab3
CONTEXT="kind-$CLUSTER_NAME"
GENERATED_CONFIG="$SOURCE_DIR/.kind-config.generated.yaml"

command -v kind >/dev/null
command -v kubectl >/dev/null
docker info >/dev/null

mkdir -p "$DEPLOY_ROOT/registry" "$DEPLOY_ROOT/shared" "$DEPLOY_ROOT/users"
DEPLOY_ROOT="$DEPLOY_ROOT" docker compose -f "$SOURCE_DIR/registry.compose.yaml" up -d
curl --fail --silent http://127.0.0.1:5001/v2/ >/dev/null

if ! kind get clusters | grep -qx "$CLUSTER_NAME"; then
    docker ps -q --filter label=com.docker.compose.project=museum-archive | while IFS= read -r container; do
        docker stop "$container"
    done

    if [[ -f "$DEPLOY_ROOT/shared/museum.db" && ! -f "$DEPLOY_ROOT/shared/museum.db.lab2-backup" ]]; then
        cp "$DEPLOY_ROOT/shared/museum.db" "$DEPLOY_ROOT/shared/museum.db.lab2-backup"
    fi

    DEPLOY_ROOT="$DEPLOY_ROOT" SOURCE_DIR="$SOURCE_DIR" GENERATED_CONFIG="$GENERATED_CONFIG" python3 - <<'PY'
import os
from pathlib import Path

source = Path(os.environ["SOURCE_DIR"]) / "k8s/kind-config.yaml.template"
root = Path(os.environ["DEPLOY_ROOT"]).resolve()
config = source.read_text(encoding="utf-8").replace("__DEPLOY_ROOT__", str(root))
Path(os.environ["GENERATED_CONFIG"]).write_text(config, encoding="utf-8")
PY
    kind create cluster --name "$CLUSTER_NAME" --config "$GENERATED_CONFIG"
fi

REGISTRY_ID="$(DEPLOY_ROOT="$DEPLOY_ROOT" docker compose -f "$SOURCE_DIR/registry.compose.yaml" ps -q registry)"
REGISTRY_NAME="$(docker inspect -f '{{.Name}}' "$REGISTRY_ID")"
REGISTRY_NAME="${REGISTRY_NAME#/}"
if [[ "$(docker inspect -f '{{json .NetworkSettings.Networks.kind}}' "$REGISTRY_ID")" == "null" ]]; then
    docker network connect kind "$REGISTRY_ID"
fi

for node in $(kind get nodes --name "$CLUSTER_NAME"); do
    registry_dir=/etc/containerd/certs.d/localhost:5001
    docker exec "$node" mkdir -p "$registry_dir"
    printf '[host."http://%s:5000"]\n  capabilities = ["pull", "resolve"]\n' "$REGISTRY_NAME" |
        docker exec -i "$node" tee "$registry_dir/hosts.toml" >/dev/null
done

kubectl --context "$CONTEXT" get nodes
echo 'Cluster and registry are ready.'
