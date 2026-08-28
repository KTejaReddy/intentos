const BASE = "";

async function request<T>(method: string, path: string, body?: any): Promise<T> {
  const res = await fetch(BASE + path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<any>("GET", "/api/health"),

  // intent pipeline
  analyze: (idea: string) => request<any>("POST", "/api/intent/analyze", { idea }),
  requirements: (idea: string) => request<any>("POST", "/api/requirements/analyze", { idea }),
  plan: (idea: string, intent?: any, answers?: Record<string, string>) =>
    request<any>("POST", "/api/plan/generate", { idea, intent, answers }),

  // compiler
  compile: (source: string, filename = "app.intentlang", options: any = {}) =>
    request<any>("POST", "/api/compile", { source, filename, options }),
  check: (source: string, filename = "app.intentlang") =>
    request<any>("POST", "/api/compile/check", { source, filename }),
  autocomplete: (source: string, line: number, col: number) =>
    request<any[]>("POST", "/api/compile/autocomplete", { source, line, col }),

  // chat (SSE)
  chat: (messages: ChatMsg[], project_id?: string) => {
    return fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, project_id }),
    });
  },

  // projects
  projects: () => request<any[]>("GET", "/api/projects"),
  createProject: (name: string, idea: string) =>
    request<any>("POST", "/api/projects", { name, idea }),
  projectFiles: (pid: string) => request<{ files: ProjectFile[] }>("GET", `/api/projects/${pid}/files`),
  readFile: (pid: string, path: string) =>
    request<{ path: string; content: string }>("GET", `/api/projects/${pid}/file?path=${encodeURIComponent(path)}`),
  writeFile: (pid: string, path: string, content: string) =>
    request<any>("PUT", `/api/projects/${pid}/file`, { path, content }),
  projectCompile: (pid: string, source: string, filename: string, options: any = {}) =>
    request<any>("POST", `/api/projects/${pid}/compile`, { source, filename, options }),
  build: (pid: string) => request<any>("POST", `/api/projects/${pid}/build`),
  run: (pid: string) => request<{ ok: boolean; preview_url: string }>("POST", `/api/projects/${pid}/run`),

  // db viewer
  dbTables: (pid: string) => request<{ tables: TableInfo[] }>("GET", `/api/projects/${pid}/db/tables`),
  dbTable: (pid: string, table: string) =>
    request<{ columns: string[]; rows: any[][] }>("GET", `/api/projects/${pid}/db/table/${table}`),

  // git
  gitStatus: (pid: string) => request<{ items: GitItem[] }>("GET", `/api/projects/${pid}/git/status`),
  gitDiff: (pid: string) => request<{ diff: string }>("GET", `/api/projects/${pid}/git/diff`),
  gitLog: (pid: string) => request<{ commits: GitCommit[] }>("GET", `/api/projects/${pid}/git/log`),

  // plugins & settings
  plugins: () => request<{ plugins: PluginInfo[] }>("GET", "/api/plugins"),
  togglePlugin: (id: string) => request<any>("POST", `/api/plugins/${id}/toggle`),
  getSettings: () => request<any>("GET", "/api/settings"),
  putSettings: (s: any) => request<any>("PUT", "/api/settings", s),
};

export type ChatMsg = { role: string; content: string };
import type { ProjectFile, TableInfo, GitItem, GitCommit, PluginInfo } from "../types";
