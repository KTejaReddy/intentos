"""Standalone preview generator.

Produces a single self-contained ``preview/index.html`` that renders the
whole application (hash router, forms, tables, toasts) with zero build step
and zero dependencies. The IR is embedded as JSON. This powers the IDE's
Preview pane: generated artifacts are served as-is and work immediately.

API calls go to ``window.INTENTOS_API`` (or the same origin) so the preview
can talk to a running backend.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Optional

from ..artifact import ArtifactSet
from ..diagnostics import Diagnostics
from ._util import js_str, resolve_model, theme_color, theme_light
from .base import Generator

if TYPE_CHECKING:  # pragma: no cover
    from .. import ir as I
    from ..compiler import CompileOptions


class StandaloneGenerator(Generator):
    name = "preview/standalone"

    def generate(self, module: "I.ModuleIR", options: "CompileOptions",
                 artifacts: ArtifactSet, diags: Diagnostics) -> None:
        data = json.dumps(module.to_dict(), separators=(",", ":"))
        primary = theme_color(module.app.theme)
        light = theme_light(module.app.theme)
        html = _TEMPLATE.replace("__IR_JSON__", data) \
            .replace("__TITLE__", js_str(module.app.title)) \
            .replace("__PRIMARY__", primary) \
            .replace("__LIGHT__", light)
        artifacts.add("preview/index.html", html, self.name)


_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>__TITLE__</title>
<style>
  :root { --primary: __PRIMARY__; --primary-light: __LIGHT__; --bg:#0b0f1a; --panel:#131a2b; --border:rgba(255,255,255,.08); --text:#e6eaf3; --muted:#8b94a7; }
  * { box-sizing: border-box; }
  body { margin:0; font-family: Inter, system-ui, sans-serif; background: var(--bg); color: var(--text); }
  .page { max-width: 960px; margin: 0 auto; padding: 24px 20px 80px; display: flex; flex-direction: column; gap: 14px; }
  .navbar { position: sticky; top: 0; background: rgba(11,15,26,.88); backdrop-filter: blur(10px); border-bottom: 1px solid var(--border); display: flex; gap: 4px; padding: 10px 20px; }
  .nav-link { color: var(--muted); text-decoration: none; padding: 6px 12px; border-radius: 8px; }
  .nav-link.active, .nav-link:hover { color: var(--text); background: rgba(255,255,255,.06); }
  .card { background: linear-gradient(160deg, rgba(255,255,255,.06), rgba(255,255,255,.02)); border: 1px solid var(--border); border-radius: 14px; padding: 24px; }
  .field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; font-size: 13px; color: var(--muted); }
  .field input, .field select, .field textarea { background: rgba(255,255,255,.04); border: 1px solid var(--border); border-radius: 10px; padding: 10px 12px; color: var(--text); font-size: 14px; outline: none; }
  .field input:focus { border-color: var(--primary); }
  .btn { border: 0; border-radius: 10px; padding: 10px 18px; font-size: 14px; cursor: pointer; font-weight: 600; }
  .btn-primary { background: linear-gradient(135deg, var(--primary), var(--primary-light)); color: #0b0f1a; }
  .text.title { font-size: 34px; font-weight: 800; } .text.heading { font-size: 22px; font-weight: 700; } .text.subtitle { color: var(--muted); }
  .data-table { width: 100%; border-collapse: collapse; }
  .data-table th { text-align: left; padding: 10px; color: var(--muted); font-size: 12px; text-transform: uppercase; border-bottom: 1px solid var(--border); }
  .data-table td { padding: 10px; border-bottom: 1px solid var(--border); font-size: 14px; }
  .table-card { overflow: auto; border: 1px solid var(--border); border-radius: 12px; }
  .badge { background: color-mix(in srgb, var(--primary) 20%, transparent); color: var(--primary-light); padding: 2px 10px; border-radius: 999px; font-size: 12px; }
  .toast-host { position: fixed; bottom: 24px; left: 50%; transform: translateX(-50%); display: flex; flex-direction: column; gap: 8px; z-index: 100; }
  .toast { background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 18px; box-shadow: 0 8px 24px rgba(0,0,0,.4); }
  .empty { color: var(--muted); }
</style>
</head>
<body>
<div id="app"></div>
<script>
const IR = __IR_JSON__;
const API = window.INTENTOS_API || '';
function esc(s) { return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c])); }
function toast(msg) {
  let host = document.querySelector('.toast-host');
  if (!host) { host = document.createElement('div'); host.className = 'toast-host'; document.body.appendChild(host); }
  const el = document.createElement('div'); el.className = 'toast'; el.textContent = msg;
  host.appendChild(el); setTimeout(() => el.remove(), 3200);
}
const routes = {}; IR.pages.forEach(p => routes[p.route] = p);
const pageByName = {}; IR.pages.forEach(p => pageByName[p.name.toLowerCase()] = p);
const apiByName = {}; IR.apis.forEach(a => apiByName[a.name.toLowerCase()] = a);
function current() { return window.location.hash.replace(/^#/, '') || '/'; }
function go(route) { window.location.hash = '#' + route; }
function nav() {
  const c = current();
  return '<nav class="navbar">' + IR.pages.map(p => `<a class="nav-link ${c === p.route ? 'active' : ''}" href="#${p.route}">${esc(p.title || p.name)}</a>`).join('') + '</nav>';
}
async function apiCall(a, payload) {
  const headers = { 'Content-Type': 'application/json' };
  const token = localStorage.getItem('intentos_token');
  if (token) headers['Authorization'] = 'Bearer ' + token;
  const res = await fetch(API + a.route, { method: a.method, headers, body: payload ? JSON.stringify(payload) : undefined });
  if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail || d; } catch {} throw new Error(d); }
  return res.json();
}
async function runActions(actions, ctx, depth) {
  for (const act of actions) {
    if (act.kind === 'navigate_to' || act.kind === 'open') {
      const p = pageByName[act.target.toLowerCase()]; if (p) go(p.route); else toast('Page not found: ' + act.target);
    } else if (act.kind === 'show_toast') { toast(act.value); }
    else if (act.kind === 'call_api') {
      const a = apiByName[act.target.toLowerCase()];
      if (!a) { toast('API not found: ' + act.target); continue; }
      try {
        const r = await apiCall(a, ctx.payload);
        for (const h of act.handlers || []) {
          if (h.event === 'success') await runActions(h.actions, { payload: r }, depth + 1);
        }
      } catch (e) {
        for (const h of act.handlers || []) {
          if (h.event === 'failure') await runActions(h.actions, {}, depth + 1);
        }
        if (!(act.handlers || []).some(h => h.event === 'failure')) toast(e.message || 'request failed');
      }
    } else if (act.kind === 'submit') {
      try { await apiCall(ctx.api, ctx.payload); toast('submitted'); } catch (e) { toast(e.message || 'submit failed'); }
    }
  }
}
// Helpers keep generated markup free of nested-quote hazards.
function noHandler() { toast('no handler'); }
function submitForm(name) {
  const a = apiByName[String(name).toLowerCase()];
  if (!a) { toast('API not found: ' + name); return; }
  try { apiCall(a, window.__state || {}).then(() => toast('submitted')).catch(e => toast(e.message || 'submit failed')); }
  catch (e) { toast(e.message || 'submit failed'); }
}
function widgetHTML(w, ctx, state) {
  const p = w.props || {};
  const slug = w.name.toLowerCase().replace(/[^a-z0-9]+/g, '_');
  switch (w.kind) {
    case 'navbar':
      return nav();
    case 'text': {
      const tag = (p.variant === 'title') ? 'h1' : (p.variant === 'heading') ? 'h2' : 'p';
      return `<${tag} class="text ${esc(p.variant || 'body')}">${esc(p.text || w.name)}</${tag}>`;
    }
    case 'image': return `<img src="${esc(p.src || '')}" alt="${esc(p.alt || w.name)}" style="max-width:100%;border-radius:12px" />`;
    case 'link': return `<a class="nav-link" href="${esc(p.href || '#')}">${esc(p.text || w.name)}</a>`;
    case 'badge': return `<span class="badge">${esc(p.text || w.name)}</span>`;
    case 'card': return `<div class="card"><h3>${esc(p.title || w.name)}</h3></div>`;
    case 'input': case 'textarea': case 'select': case 'checkbox': {
      const key = slug; state[key] = state[key] || '';
      const set = `oninput="window.__state.${key}=this.value;render()"`;
      const label = `<label class="field">${esc(p.label || w.name)}`;
      if (w.kind === 'textarea') return label + `<textarea ${set}>${esc(state[key])}</textarea></label>`;
      if (w.kind === 'select') {
        const opts = (p.options || []).map(o => `<option>${esc(o)}</option>`).join('');
        return label + `<select ${set}>${opts}</select></label>`;
      }
      if (w.kind === 'checkbox') return `<label class="field"><input type="checkbox" ${state[key] ? 'checked' : ''} oninput="window.__state.${key}=this.checked;render()" />${esc(p.label || w.name)}</label>`;
      const type = p.type === 'password' ? 'password' : 'text';
      return label + `<input type="${type}" value="${esc(state[key])}" ${set} placeholder="${esc(p.placeholder || '')}" /></label>`;
    }
    case 'table': case 'chart': {
      const a = apiByName[String(p.api || '').toLowerCase()];
      if (!a) return `<div class="card">Table ${esc(w.name)}</div>`;
      const key = 'load_' + slug;
      if (!state[key]) {
        state[key] = true;
        apiCall(a).then(r => { state[slug] = Array.isArray(r) ? r : (r.items || []); render(); }).catch(() => { state[slug] = []; render(); });
      }
      const rows = state[slug] || [];
      const model = IR.models.find(m => m.table === (a.query && a.query.table)) || IR.models[0];
      const cols = model ? model.fields.map(f => f.name) : Object.keys(rows[0] || {});
      if (w.kind === 'chart') {
        return '<div class="card"><div style="display:flex;align-items:flex-end;gap:6px;height:160px">' +
          rows.slice(0, 12).map(r => `<div style="width:24px;background:linear-gradient(180deg,var(--primary-light),var(--primary));border-radius:6px 6px 0 0;height:${30 + (Number(r.value) || 30) % 130}px"></div>`).join('') + '</div></div>';
      }
      return '<div class="table-card"><table class="data-table"><thead><tr>' + cols.map(c => `<th>${esc(c)}</th>`).join('') + '</tr></thead><tbody>' +
        rows.map(r => '<tr>' + cols.map(c => `<td>${esc(r[c])}</td>`).join('') + '</tr>').join('') + '</tbody></table></div>';
    }
    case 'button': {
      const a = apiByName[String(p.api || '').toLowerCase()];
      const label = esc(p.label || w.name);
      const h = (w.events || []).map(ev => {
        const key = 'h_' + slug + '_' + ev.event.replace(/[^a-z0-9]+/g, '_');
        state[key] = () => runActions(ev.actions, { payload: undefined }, 0);
        return key;
      })[0];
      return `<button class="btn btn-primary" onclick="${h ? 'window.__state.' + h + '()' : 'noHandler()'}">${label}</button>`;
    }
    case 'form': {
      let inner = '';
      for (const child of w.children || []) inner += widgetHTML(child, ctx, state);
      const a = apiByName[String(p.api || '').toLowerCase()];
      return `<form class="card" data-api="${esc(p.api || '')}" onsubmit="event.preventDefault();submitForm(this.dataset.api)">${inner}</form>`;
    }
    default: return `<div>${esc(w.name)}</div>`;
  }
}
function render() {
  if (!window.__state) window.__state = {};
  const state = window.__state;
  const page = routes[current()] || routes['/'];
  const app = document.getElementById('app');
  if (!page) { app.innerHTML = nav() + '<div class="page">Not found</div>'; return; }
  let body = '';
  for (const w of page.widgets || []) body += widgetHTML(w, {}, state);
  if (!body) body = '<div class="page empty">This page has no widgets yet.</div>';
  app.innerHTML = nav() + '<div class="page">' + body + '</div>';
}
window.addEventListener('hashchange', render);
render();
</script>
</body>
</html>
"""
