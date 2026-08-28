import * as monaco from "monaco-editor";
import { COMPLETION_WORDS, INTENTLANG_ID } from "./monarch";
import { api } from "../api/client";
import type { CompileResult } from "../types";

let checkTimer: number | null = null;
let latestModel: monaco.editor.ITextModel | null = null;
let lastUri = "";

export function installIntentLangProviders(onDiagnostics: (r: CompileResult) => void) {
  monaco.languages.registerCompletionItemProvider(INTENTLANG_ID, {
    triggerCharacters: [" ", "C", "c"],
    provideCompletionItems: async (model, position) => {
      const word = model.getWordUntilPosition(position);
      const prefix = word.word.toLowerCase();
      const suggestions: monaco.languages.CompletionItem[] = [];

      const range: monaco.IRange = {
        startLineNumber: position.lineNumber,
        startColumn: word.startColumn,
        endLineNumber: position.lineNumber,
        endColumn: word.endColumn,
      };

      // static keywords
      for (const w of COMPLETION_WORDS) {
        if (!prefix || w.toLowerCase().startsWith(prefix)) {
          suggestions.push({
            label: w,
            kind: monaco.languages.CompletionItemKind.Keyword,
            insertText: w + (w.endsWith(" ") ? "" : " "),
            range,
            detail: "IntentLang",
          });
        }
      }

      // dynamic symbols from the backend
      try {
        const text = model.getValue();
        const line = position.lineNumber - 1;
        const col = position.column - 1;
        const res = await api.autocomplete(text, line, col);
        for (const c of res) {
          suggestions.push({
            label: c.label,
            kind: monaco.languages.CompletionItemKind.Class,
            insertText: c.label,
            range,
            detail: c.detail || c.kind,
          });
        }
      } catch {
        /* backend offline — keywords only */
      }
      return { suggestions: suggestions.slice(0, 120) };
    },
  });

  monaco.languages.registerHoverProvider(INTENTLANG_ID, {
    provideHover(model, position) {
      const word = model.getWordAtPosition(position);
      if (!word) return null;
      const hints: Record<string, string> = {
        Create: "Declares an application, page, model, api, role, database or job.",
        Application: "The top-level product: name, title, theme, stack hints.",
        Page: "A screen with widgets (Add ...) and events (When ...).",
        Model: "A database entity with Fields; maps to a table.",
        Api: "An HTTP endpoint with Method, Route, Auth, Request, Query, Response.",
        Field: "A column: Type, Required, Unique, Primary, Reference Model.Field.",
        When: "An event block: clicked, login succeeds, on load, ...",
        On: "Response handler: On Success / On Failure.",
        Call: "Call Api <Name> with On Success / On Failure handlers.",
        Navigate: "Navigate To <Page> — client-side route change.",
        Show: "Show Toast \"message\".",
        Deploy: "Deploy Docker / GithubActions — generates deployment files.",
        Use: "Use <Plugin> — activates a codegen plugin (Pwa, Seo).",
        With: "Property block: Key Value lines.",
        Type: "Field data type: string, int, boolean, email, money, enum ...",
        Auth: "public | user | admin | <RoleName>.",
      };
      const label = word.word;
      const hint = hints[label[0].toUpperCase() + label.slice(1)] || hints[label];
      if (!hint) return null;
      return {
        contents: [{ value: `**${label}** — ${hint}` }],
      };
    },
  });

  // Debounced live diagnostics via the compiler backend.
  monaco.editor.onDidCreateModel((model) => {
    if (model.getLanguageId() !== INTENTLANG_ID) return;
    model.onDidChangeContent(() => scheduleCheck(model, onDiagnostics));
  });
  monaco.editor.onDidChangeModelLanguage((e) => {
    if (e.model.getLanguageId() === INTENTLANG_ID) {
      e.model.onDidChangeContent(() => scheduleCheck(e.model, onDiagnostics));
    }
  });
}

function scheduleCheck(model: monaco.editor.ITextModel, onDiagnostics: (r: CompileResult) => void) {
  if (checkTimer !== null) window.clearTimeout(checkTimer);
  latestModel = model;
  lastUri = model.uri.toString();
  checkTimer = window.setTimeout(async () => {
    checkTimer = null;
    if (!latestModel || latestModel.uri.toString() !== lastUri) return;
    try {
      const res = await api.check(latestModel.getValue());
      const markers = toMarkers(res.diagnostics || [], latestModel);
      monaco.editor.setModelMarkers(latestModel, "intentos", markers);
      onDiagnostics(res);
    } catch {
      /* backend offline */
    }
  }, 450);
}

function toMarkers(
  diagnostics: { severity: string; message: string; line: number; col: number }[],
  model: monaco.editor.ITextModel
): monaco.editor.IMarkerData[] {
  return diagnostics
    .filter((d) => d.severity === "error" || d.severity === "warning")
    .map((d) => ({
      severity:
        d.severity === "error"
          ? monaco.MarkerSeverity.Error
          : monaco.MarkerSeverity.Warning,
      message: `[${d.severity}] ${d.message}`,
      startLineNumber: Math.max(1, d.line),
      startColumn: Math.max(1, d.col),
      endLineNumber: Math.max(1, d.line),
      endColumn: Math.max(1, d.col) + 1,
    }));
}
