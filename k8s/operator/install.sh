#!/usr/bin/env bash
set -euo pipefail

OPERATOR_VERSION="${OPERATOR_VERSION:-1.20.0}"   # pinned: change deliberately
NAMESPACE=pxc

kubectl create namespace "$NAMESPACE" --dry-run=client -o yaml | kubectl apply -f -
kubectl apply --server-side -n "$NAMESPACE" \
  -f "https://raw.githubusercontent.com/percona/percona-xtradb-cluster-operator/v${OPERATOR_VERSION}/deploy/bundle.yaml"
kubectl wait --for=condition=Available deployment --all -n "$NAMESPACE" --timeout=180s
kubectl get pods -n "$NAMESPACE"
