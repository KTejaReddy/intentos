import Editor, { type OnMount } from "@monaco-editor/react";
import { useMemo } from "react";
import { useStore } from "../../store/useStore";
import { defineIntentLang, INTENTLANG_ID } from "../../intentlang/monarch";
import { installIntentLangProviders } from "../../intentlang/editor";

let providersInstalled = false;

export default function EditorPane() {
  const { activeTab, fileContents, setContent, setDiagnostics, setCompiling, compiling, console } = useStore();

  const language = useMemo(() => {
    if (!activeTab) return "plaintext";
    if (activeTab.endsWith(".intentlang")) return INTENTLANG_ID;
    if (activeTab.endsWith(".py")) return "python";
    if (activeTab.endsWith(".ts") || activeTab.endsWith(".tsx")) return "typescript";
    if (activeTab.endsWith(".json")) return "json";
    if (activeTab.endsWith(".md")) return "markdown";
    return "plaintext";
  }, [activeTab]);

  const value = activeTab ? fileContents[activeTab] ?? "" : "";

  const onMount: OnMount = (_editor, monaco) => {
    defineIntentLang();
    monaco.editor.setTheme("intentos-dark");
    if (!providersInstalled) {
      providersInstalled = true;
      installIntentLangProviders((res) => {
        setDiagnostics(res.diagnostics || []);
      });
    }
  };

  if (!activeTab) {
    return (
      <div className="flex-1 grid place-items-center text-[var(--muted)]">
        <div className="text-center animate-fadeUp">
          <p className="text-2xl font-bold mb-2">
            Intent<span className="gradient-text">Lang</span>
          </p>
          <p className="text-[13px]">Open a .intentlang file to edit the deterministic program.</p>
          <p className="text-[12px] opacity-70 mt-1">
            English → AI Planner → IntentLang → Compiler → Application
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative flex-1 min-h-0">
      <Editor
        height="100%"
        language={language}
        value={value}
        theme="intentos-dark"
        path={activeTab}
        onMount={onMount}
        onChange={(v) => setContent(activeTab, v ?? "")}
        options={{
          fontSize: 13,
          fontFamily: "'JetBrains Mono', monospace",
          minimap: { enabled: false },
          scrollBeyondLastLine: false,
          padding: { top: 12 },
          automaticLayout: true,
          tabSize: 2,
          renderLineHighlight: "all",
          smoothScrolling: true,
          cursorBlinking: "smooth",
          folding: true,
          guides: { indentation: true, bracketPairs: true },
        }}
      />
      {compiling && (
        <div className="absolute top-2 right-3 chip text-indigo-300 bg-indigo-500/15 animate-pulseGlow">
          compiling…
        </div>
      )}
    </div>
  );
}
