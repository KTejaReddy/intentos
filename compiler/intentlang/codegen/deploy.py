"""Deployment generator — vercel.json, render.yaml, fly.toml, scripts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class DeployGenerator(Generator):
    name = "deploy"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        app = module.app
        artifacts.add("deploy/vercel.json",
                      '{\n'
                      '  "framework": "vite",\n'
                      '  "buildCommand": "npm run build",\n'
                      '  "outputDirectory": "dist",\n'
                      '  "rewrites": [{ "source": "/(.*)", "destination": "/index.html" }]\n'
                      '}\n', self.name)
        artifacts.add("deploy/render.yaml",
                      "services:\n"
                      "  - type: web\n"
                      "    name: backend\n"
                      "    runtime: python\n"
                      "    buildCommand: pip install -r requirements.txt\n"
                      "    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT\n"
                      "    envVars:\n"
                      "      - key: DATABASE_URL\n"
                      "        value: sqlite:////var/data/app.db\n"
                      "    disk:\n"
                      "      name: data\n"
                      "      mountPath: /var/data\n", self.name)
        artifacts.add("deploy/fly.toml",
                      "app = \"intentos-app\"\n"
                      "primary_region = \"sin\"\n\n"
                      "[build]\n"
                      "dockerfile = \"../infra/Dockerfile\"\n\n"
                      "[env]\n"
                      "  DATABASE_URL = \"sqlite:////data/app.db\"\n\n"
                      "[mounts]\n"
                      "  source = \"app_data\"\n"
                      "  destination = \"/data\"\n\n"
                      "[http_service]\n"
                      "  internal_port = 8000\n"
                      "  force_https = true\n"
                      "  auto_stop_machines = true\n"
                      "  auto_start_machines = true\n", self.name)
        artifacts.add("deploy/.env.production.example",
                      "DATABASE_URL=sqlite:////data/app.db\n"
                      "INTENTOS_SECRET=replace-with-a-long-random-secret\n"
                      "PORT=8000\n", self.name)
        artifacts.add("deploy/scripts/deploy.sh",
                      "#!/usr/bin/env bash\n"
                      "set -euo pipefail\n"
                      "# Deterministic deploy script (edit the targets you use)\n"
                      "case \"${1:-help}\" in\n"
                      "  docker) docker compose -f infra/docker-compose.yml up -d --build ;;\n"
                      "  fly)    fly deploy --config deploy/fly.toml ;;\n"
                      "  vercel) (cd frontend && npx vercel --prod) ;;\n"
                      "  *)\n"
                      "    echo \"usage: $0 {docker|fly|vercel}\" ;;\n"
                      "esac\n", self.name)
