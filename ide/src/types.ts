export interface Diagnostic {
  severity: "error" | "warning" | "info" | "hint";
  code: string;
  message: string;
  line: number;
  col: number;
  file: string;
  notes?: string[];
}

export interface StepTrace {
  name: string;
  elapsed_ms: number;
  ok: boolean;
  detail: string;
}

export interface CompileResult {
  ok: boolean;
  diagnostics: Diagnostic[];
  module: any;
  steps: StepTrace[];
  fingerprint: string;
  from_cache: boolean;
  total_ms: number;
  artifacts?: { files: { path: string; note: string }[]; count: number };
  zip_b64?: string;
  tokens?: any[];
  ast?: any;
  stats?: {
    memory_mb: number;
    models: number;
    apis: number;
    pages: number;
    files: number;
    determinism_status: string;
  };
}

export interface ProjectFile {
  path: string;
  size: number;
}

export interface Project {
  id: string;
  name: string;
  idea: string;
  files: string[];
  root?: string;
}

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface ConsoleLine {
  kind: "info" | "ok" | "error" | "muted" | "step";
  text: string;
  ts: number;
}

export interface PipelineStep {
  name: string;
  status: "running" | "done" | "error" | "skipped";
  detail: string;
  data?: any;
}

export interface PluginInfo {
  id: string;
  name: string;
  description: string;
  type: string;
  author: string;
  version: string;
  enabled: boolean;
}

export interface TableInfo {
  name: string;
  columns: string[];
  rows: number;
}

export interface GitItem {
  kind: string;
  status: string;
  path: string;
}

export interface GitCommit {
  hash: string;
  author: string;
  subject: string;
}

export type Activity = "explorer" | "search" | "git" | "db" | "plugins" | "settings";
export type BottomTab = "problems" | "output" | "console" | "pipeline";
