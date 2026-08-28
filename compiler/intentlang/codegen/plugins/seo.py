"""SEO plugin — activated with ``Use Seo`` in IntentLang.

Adds sitemap.xml, robots.txt, and per-page meta tags to the generated app.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ...artifact import ArtifactSet
from ...diagnostics import Diagnostics
from ..base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .... import ir as I
    from ...compiler import CompileOptions


class SeoGenerator(Generator):
    name = "plugin/seo"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        base = "https://example.com"  # replace with the deployed origin
        urls = "\n".join(
            f"  <url><loc>{base}{p.route}</loc><priority>{1.0 if p.route == '/' else 0.8}</priority></url>"
            for p in module.pages
        )
        artifacts.add(
            "frontend/public/sitemap.xml",
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + urls + "\n</urlset>\n", self.name,
        )
        artifacts.add(
            "frontend/public/robots.txt",
            "User-agent: *\nAllow: /\nSitemap: " + base + "/sitemap.xml\n",
            self.name,
        )
        metas = "\n".join(
            f'<meta name="description" content="{p.title}" />'
            for p in module.pages
        )
        artifacts.add("frontend/index.html.seo-snippet", metas + "\n", self.name)
