#!/usr/bin/env bash
set -euo pipefail
# Deterministic deploy script (edit the targets you use)
case "${1:-help}" in
  docker) docker compose -f infra/docker-compose.yml up -d --build ;;
  fly)    fly deploy --config deploy/fly.toml ;;
  vercel) (cd frontend && npx vercel --prod) ;;
  *)
    echo "usage: $0 {docker|fly|vercel}" ;;
esac
