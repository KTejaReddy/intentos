"""Code generator contracts and the generator registry.

A generator turns the IR into a set of artifacts for one target
(``frontend/react``, ``backend/fastapi``, ``db/sql``, ``deploy/docker``, ...).
Targets are activated from CompileOptions plus any ``Use <plugin>`` in the
source, which is how the plugin system plugs extra generators in without
touching the compiler core.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics

if TYPE_CHECKING:  # pragma: no cover - typing only
    from .. import ir as I
    from ..compiler import CompileOptions

import abc

class Generator(abc.ABC):
    """Base class for all code generators."""

    name: str = "base"

    @abc.abstractmethod
    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        pass

    def validate_options(self, options: "CompileOptions") -> Optional[str]:
        """Return an error message if options are unsupported, else None."""
        return None


class Registry:
    def __init__(self) -> None:
        self._targets: dict[str, Generator] = {}

    def register(self, name: str, generator: Generator) -> None:
        self._targets[name] = generator

    def get(self, name: str) -> Optional[Generator]:
        return self._targets.get(name)

    def has(self, name: str) -> bool:
        return name in self._targets

    def names(self) -> list[str]:
        return sorted(self._targets)

    def resolve(self, module: "I.ModuleIR", options: "CompileOptions") -> list[Generator]:
        """Ordered list of generators active for a compile."""
        active: list[Generator] = []
        seen: set[str] = set()

        def add(target: str) -> None:
            gen = self._targets.get(target)
            if gen is not None and target not in seen:
                seen.add(target)
                active.append(gen)

        add(f"frontend/{options.frontend}")
        add(f"backend/{options.backend}")
        add("db/sql")
        add("infra/docker")
        add("ci/github-actions")
        add("docs")
        add("tests")
        add("deploy")
        add("preview/standalone")

        for plugin in module.plugins:
            add(f"plugin/{plugin.lower()}")

        for plugin in options.plugins:
            add(f"plugin/{plugin.lower()}")
        return active
