"""PWA plugin — activated with ``Use Pwa`` in IntentLang.

Adds a web manifest, an offline service worker, and an installable-app
bootstrap to the generated frontend.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

from ...artifact import ArtifactSet
from ...diagnostics import Diagnostics
from ..base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .... import ir as I
    from ...compiler import CompileOptions


class PwaGenerator(Generator):
    name = "plugin/pwa"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        manifest = {
            "name": module.app.title,
            "short_name": module.app.title[:12],
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0b0f1a",
            "theme_color": "#6366f1",
            "icons": [
                {"src": "icon.svg", "sizes": "any", "type": "image/svg+xml"},
            ],
        }
        artifacts.add("frontend/public/manifest.webmanifest",
                      json.dumps(manifest, indent=2) + "\n", self.name)
        artifacts.add("frontend/public/icon.svg", _ICON, self.name)
        artifacts.add("frontend/public/sw.js", _SW, self.name)
        artifacts.add("frontend/index.html.pwa-snippet",
                      '<link rel="manifest" href="/manifest.webmanifest" />\n'
                      '<meta name="theme-color" content="#0b0f1a" />\n'
                      '<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js")</script>\n',
                      self.name)


_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" rx="96" fill="#0b0f1a"/>
  <path d="M120 180c0-22 18-40 40-40h192c22 0 40 18 40 40v152c0 22-18 40-40 40H160c-22 0-40-18-40-40V180z" fill="#6366f1"/>
  <path d="M176 216h160M176 264h160M176 312h96" stroke="#e6eaf3" stroke-width="24" stroke-linecap="round"/>
</svg>
"""

_SW = """// IntentOS PWA service worker (generated)
const CACHE = 'intentos-v1'
self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(['/', '/index.html'])))
})
self.addEventListener('fetch', (e) => {
  e.respondWith(
    fetch(e.request)
      .then((r) => {
        const copy = r.clone()
        caches.open(CACHE).then((c) => c.put(e.request, copy))
        return r
      })
      .catch(() => caches.match(e.request).then((r) => r || caches.match('/')))
  )
})
"""
