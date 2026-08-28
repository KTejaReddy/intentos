"""Generator registry: maps target names to generator instances.

New generators (first-party or plugin) register here. Plugin generators are
activated at compile time when the module's IntentLang source contains
``Use <Plugin>`` — no core compiler changes required.
"""

from __future__ import annotations

from .base import Registry

_registry: Registry | None = None


def register_all(registry: Registry) -> None:
    from .backend_express import ExpressGenerator
    from .backend_fastapi import FastApiGenerator
    from .backend_spring import SpringGenerator
    from .db_sql import SqlGenerator
    from .deploy import DeployGenerator
    from .docker import DockerGenerator
    from .docs import DocsGenerator
    from .frontend_flutter import FlutterGenerator
    from .frontend_next import NextGenerator
    from .frontend_react import ReactGenerator
    from .github_actions import GitHubActionsGenerator
    from .standalone import StandaloneGenerator
    from .tests import TestsGenerator
    from .plugins.pwa import PwaGenerator
    from .plugins.seo import SeoGenerator

    registry.register("frontend/react", ReactGenerator())
    registry.register("frontend/next", NextGenerator())
    registry.register("frontend/flutter", FlutterGenerator())
    registry.register("backend/fastapi", FastApiGenerator())
    registry.register("backend/express", ExpressGenerator())
    registry.register("backend/spring", SpringGenerator())
    registry.register("db/sql", SqlGenerator())
    registry.register("infra/docker", DockerGenerator())
    registry.register("ci/github-actions", GitHubActionsGenerator())
    registry.register("docs", DocsGenerator())
    registry.register("tests", TestsGenerator())
    registry.register("deploy", DeployGenerator())
    registry.register("preview/standalone", StandaloneGenerator())
    registry.register("plugin/pwa", PwaGenerator())
    registry.register("plugin/seo", SeoGenerator())


def global_registry() -> Registry:
    global _registry
    if _registry is None:
        _registry = Registry()
        register_all(_registry)
    return _registry
