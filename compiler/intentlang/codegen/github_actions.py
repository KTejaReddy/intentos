"""GitHub Actions generator: CI pipeline + CD workflow."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class GitHubActionsGenerator(Generator):
    name = "ci/github-actions"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        artifacts.add(".github/workflows/ci.yml", _CI, self.name)
        artifacts.add(".github/workflows/deploy.yml", _CD, self.name)
        artifacts.add(".github/README.md",
                      "CI runs backend tests, frontend build and Docker build "
                      "on every push. CD deploys on tags.\n", self.name)


_CI = """name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install
        run: |
          pip install -r backend/requirements.txt
          pip install pytest
      - name: Test
        run: pytest backend/tests -q

  frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - name: Install
        run: npm ci
        working-directory: frontend
      - name: Build
        run: npm run build
        working-directory: frontend

  docker:
    needs: [backend, frontend]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -f infra/Dockerfile -t intentos-app:ci .
"""

_CD = """name: Deploy

on:
  push:
    tags: ["v*"]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Build image
        run: docker build -f infra/Dockerfile -t intentos-app:latest .
      - name: Push
        env:
          REGISTRY: ${{ secrets.REGISTRY }}
        run: |
          echo "${{ secrets.REGISTRY_PASSWORD }}" | docker login $REGISTRY -u "${{ secrets.REGISTRY_USERNAME }}" --password-stdin
          docker tag intentos-app:latest $REGISTRY/intentos-app:latest
          docker push $REGISTRY/intentos-app:latest
      - name: Deploy
        env:
          SSH_KEY: ${{ secrets.SSH_KEY }}
          SSH_HOST: ${{ secrets.SSH_HOST }}
        run: |
          mkdir -p ~/.ssh && echo "$SSH_KEY" > ~/.ssh/id_ed25519 && chmod 600 ~/.ssh/id_ed25519
          ssh -o StrictHostKeyChecking=no $SSH_HOST "cd /opt/intentos-app && docker compose pull && docker compose up -d"
"""
