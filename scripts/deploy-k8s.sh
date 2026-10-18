#!/usr/bin/env bash

set -Eeuo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:?Set IMAGE_TAG to the published commit tag}"
CONTEXT=kind-museum-lab3
NAMESPACE=museum

kubectl --context "$CONTEXT" get nodes >/dev/null
kubectl --context "$CONTEXT" apply -f "$SOURCE_DIR/k8s/namespace.yaml"
kubectl --context "$CONTEXT" apply -f "$SOURCE_DIR/k8s/storage.yaml"
kubectl --context "$CONTEXT" apply -f "$SOURCE_DIR/k8s/services.yaml"

kubectl --context "$CONTEXT" -n "$NAMESPACE" create configmap museum-nginx \
    --from-file=default.conf="$SOURCE_DIR/nginx/k8s.conf" \
    --dry-run=client -o yaml | kubectl --context "$CONTEXT" apply -f -

WORK_DIR="$(mktemp -d)"
trap 'rm -rf "$WORK_DIR"' EXIT
SOURCE_DIR="$SOURCE_DIR" WORK_DIR="$WORK_DIR" IMAGE_TAG="$IMAGE_TAG" python3 - <<'PY'
import os
from pathlib import Path

source = Path(os.environ["SOURCE_DIR"]) / "k8s"
destination = Path(os.environ["WORK_DIR"])
tag = os.environ["IMAGE_TAG"]
for name in ("init-jobs.yaml", "workloads.yaml"):
    template = (source / (name + ".template")).read_text(encoding="utf-8")
    (destination / name).write_text(template.replace("__IMAGE_TAG__", tag), encoding="utf-8")
PY

kubectl --context "$CONTEXT" apply -f "$WORK_DIR/init-jobs.yaml"
kubectl --context "$CONTEXT" -n "$NAMESPACE" wait --for=condition=complete \
    "job/museum-core-init-$IMAGE_TAG" --timeout=240s
kubectl --context "$CONTEXT" -n "$NAMESPACE" wait --for=condition=complete \
    "job/museum-users-init-$IMAGE_TAG" --timeout=240s

kubectl --context "$CONTEXT" apply -f "$WORK_DIR/workloads.yaml"
kubectl --context "$CONTEXT" -n "$NAMESPACE" rollout restart deployment/museum-web
for deployment in museum-core museum-users museum-web; do
    kubectl --context "$CONTEXT" -n "$NAMESPACE" rollout status \
        "deployment/$deployment" --timeout=240s
done
kubectl --context "$CONTEXT" -n "$NAMESPACE" get deployments,pods,services,pvc
