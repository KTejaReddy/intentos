"""Docker generator: Dockerfile, docker-compose.yml, .dockerignore."""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class DockerGenerator(Generator):
    name = "infra/docker"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        app = module.app
        artifacts.add("infra/Dockerfile", _DOCKERFILE, self.name)
        artifacts.add("infra/.dockerignore", _DOCKERIGNORE, self.name)
        artifacts.add("infra/docker-compose.yml",
                      self._compose(options.database), self.name)
        artifacts.add("infra/README.md",
                      "# Infrastructure\n\n"
                      "```bash\n"
                      "cd infra\n"
                      "docker compose up --build\n"
                      "```\n"
                      f"The {app.backend} backend listens on http://localhost:8000.\n",
                      self.name)

    def _compose(self, db: str) -> str:
        backend = {
            "image": "build: .",
            "build": {"context": "..", "dockerfile": "infra/Dockerfile"},
            "ports": ["8000:8000"],
            "environment": ["DATABASE_URL=sqlite:////data/app.db"],
            "volumes": ["app-data:/data"],
            "restart": "unless-stopped",
        }
        services = ["  backend:"]
        for key, val in backend.items():
            services.append(f"    {key}: {self._yaml(val, 4)}")
        if db == "postgres":
            services.extend([
                "  db:",
                "    image: postgres:16-alpine",
                "    environment:",
                "      POSTGRES_USER: ${POSTGRES_USER:-postgres}",
                "      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}",
                "      POSTGRES_DB: ${POSTGRES_DB:-app}",
                "    volumes:",
                "      - pg-data:/var/lib/postgresql/data",
            ])
        elif db == "mysql":
            services.extend([
                "  db:",
                "    image: mysql:8",
                "    environment:",
                "      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD:-root}",
                "      MYSQL_DATABASE: ${MYSQL_DATABASE:-app}",
                "    volumes:",
                "      - mysql-data:/var/lib/mysql",
            ])
        volumes = ["volumes:", "  app-data:"]
        if db in ("postgres", "mysql"):
            volumes.append(f"  {db}-data:" if db == "postgres" else "  mysql-data:")
        return "services:\n" + "\n".join(services) + "\n" + "\n".join(volumes) + "\n"

    @staticmethod
    def _yaml(val, indent: int) -> str:
        pad = " " * indent
        if isinstance(val, dict):
            return "\n".join(f"{pad}{k}: {v}" for k, v in val.items())
        if isinstance(val, list):
            return "\n" + "\n".join(f"{pad}- {v}" for v in val)
        return str(val)


_DOCKERFILE = """# IntentOS generated image (FastAPI backend)
FROM python:3.12-slim

WORKDIR /app
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
WORKDIR /app/backend

ENV DATABASE_URL=sqlite:////data/app.db
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "python -m uvicorn main:app --host 0.0.0.0 --port ${PORT}"]
"""

_DOCKERIGNORE = """__pycache__/
*.pyc
.env
.venv/
node_modules/
.git/
.cache/
"""
