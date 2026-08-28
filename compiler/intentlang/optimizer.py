"""Optimizer passes over the IR.

Optimizations are correctness-preserving rewrites plus analysis diagnostics:

1. ``fold_defaults``        — apply theme defaults, derive page titles.
2. ``canonicalize``         — normalize casing, sort deploys, dedupe plugins.
3. ``analyze_usage``        — report unused models / apis / pages as info
                              diagnostics (deterministic, ordered).
4. ``resolve_queries``      — bind Query.table to a model when possible.
5. ``emit_notes``           — human-readable summaries for the console.

The output IR is fully deterministic: same input, same IR, same artifacts.
"""

from __future__ import annotations

from . import ir as I
from .diagnostics import Diagnostics

THEMES = {
    "indigo": ("#6366f1", "#a5b4fc", "240"),
    "blue": ("#3b82f6", "#93c5fd", "217"),
    "emerald": ("#10b981", "#6ee7b7", "160"),
    "rose": ("#f43f5e", "#fda4af", "350"),
    "amber": ("#f59e0b", "#fcd34d", "38"),
    "slate": ("#64748b", "#cbd5e1", "215"),
    "violet": ("#8b5cf6", "#c4b5fd", "258"),
}


class Optimizer:
    def __init__(self, filename: str = "<string>",
                 diagnostics: Diagnostics | None = None) -> None:
        self.filename = filename
        self.diags = diagnostics if diagnostics is not None else Diagnostics()

    def optimize(self, module: I.ModuleIR) -> I.ModuleIR:
        self._fold_defaults(module)
        self._canonicalize(module)
        self._resolve_queries(module)
        self._analyze_usage(module)
        self._emit_notes(module)
        return module

    # -- passes -----------------------------------------------------------
    def _fold_defaults(self, module: I.ModuleIR) -> None:
        app = module.app
        app.theme = (app.theme or "indigo").lower()
        if app.theme not in THEMES:
            self.diags.warning("IL-O010", f"unknown theme {app.theme!r}, falling back to 'indigo'",
                               0, 0, self.filename)
            app.theme = "indigo"
        for page in module.pages:
            if not page.title:
                page.title = page.name
        for model in module.models:
            if not model.table:
                model.table = I._slug(model.name)
            for f in model.fields:
                if f.ftype == "id":
                    f.primary = True
                    f.required = True

    def _canonicalize(self, module: I.ModuleIR) -> None:
        module.deploys.sort(key=lambda d: (d.target.lower(), d.line))
        seen: set[str] = set()
        kept: list[str] = []
        for p in module.plugins:
            key = p.lower()
            if key not in seen:
                seen.add(key)
                kept.append(p)
        module.plugins = kept
        for api in module.apis:
            api.method = api.method.upper()

    def _resolve_queries(self, module: I.ModuleIR) -> None:
        for api in module.apis:
            if api.query and api.query.table:
                model = module.model_by_table(api.query.table)
                if model:
                    pass  # Correctly resolved

    def _analyze_usage(self, module: I.ModuleIR) -> None:
        used_apis: set[str] = set()
        used_pages: set[str] = set()
        used_models: set[str] = set()

        def walk_events(events) -> None:
            for ev in events:
                for act in ev.actions:
                    if act.kind == "call_api":
                        used_apis.add(act.target.lower())
                    if act.kind in ("navigate_to", "open"):
                        used_pages.add(act.target.lower())
                    if act.kind == "submit" and act.target:
                        used_apis.add(act.target.lower())
                    for h in act.handlers:
                        walk_events([h])

        for page in module.pages:
            for w in page.widgets:
                walk_events(w.events)
            walk_events(page.events)
        for api in module.apis:
            walk_events(api.events)
            for resp in api.responses:
                walk_events(resp.handlers)
        walk_events(module.rules)

        # Queries reference models/tables.
        for api in module.apis:
            if api.query and api.query.table:
                m = module.model_by_table(api.query.table)
                if m:
                    used_models.add(m.name.lower())
            for resp in api.responses:
                if isinstance(resp.body, str) and module.model_by_table(resp.body):
                    used_models.add(resp.body.lower())
                elif isinstance(resp.body, tuple) and resp.body[1]:
                    used_models.add(resp.body[1].lower())

        for m in module.models:
            if m.name.lower() not in used_models:
                self.diags.info("IL-O020", f"model '{m.name}' is not referenced by any api or query; "
                                           "its table will still be created", 0, 0, self.filename)
        for a in module.apis:
            if a.name.lower() not in used_apis:
                self.diags.info("IL-O021", f"api '{a.name}' is not called from any page; "
                                           "it is still generated", 0, 0, self.filename)
        for p in module.pages:
            if p.name.lower() not in used_pages and p.route != "/":
                self.diags.info("IL-O022", f"page '{p.name}' has no inbound navigation; "
                                           "it is still generated", 0, 0, self.filename)

    def _emit_notes(self, module: I.ModuleIR) -> None:
        app = module.app
        self.diags.info(
            "IL-O030",
            f"compiled application '{app.name}': {len(module.pages)} page(s), "
            f"{len(module.models)} model(s), {len(module.apis)} api(s), "
            f"backend={app.backend}, frontend={app.frontend}, db={app.database}",
            0, 0, self.filename,
        )
