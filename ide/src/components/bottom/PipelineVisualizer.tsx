import { useState } from "react";
import { useStore } from "../../store/useStore";

export default function PipelineVisualizer() {
  const { bottomTab, buildResult } = useStore();
  const [subTab, setSubTab] = useState<"tokens" | "ast" | "ir" | "benchmarks">("benchmarks");

  if (bottomTab !== "pipeline") return null;

  if (!buildResult) {
    return (
      <div className="h-full flex items-center justify-center text-[var(--muted)] text-sm">
        Compile the project to view the pipeline.
      </div>
    );
  }

  const { tokens, ast, module, stats } = buildResult;

  return (
    <div className="h-full flex flex-col bg-[#111111] overflow-hidden">
      <div className="flex items-center gap-2 px-4 h-8 border-b border-white/5 bg-white/[0.02]">
        {["benchmarks", "tokens", "ast", "ir"].map((t) => (
          <button
            key={t}
            onClick={() => setSubTab(t as any)}
            className={`text-xs px-2 py-1 rounded transition-colors ${
              subTab === t ? "bg-white/10 text-white" : "text-[var(--muted)] hover:text-white"
            }`}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-auto p-4 font-mono text-[11px] leading-relaxed">
        {subTab === "benchmarks" && stats && (
          <div className="grid grid-cols-2 gap-4 max-w-lg">
            <div className="bg-white/5 p-3 rounded border border-white/10">
              <div className="text-[var(--muted)] mb-1">Compilation Time</div>
              <div className="text-xl text-green-400">{buildResult.total_ms.toFixed(2)} ms</div>
            </div>
            <div className="bg-white/5 p-3 rounded border border-white/10">
              <div className="text-[var(--muted)] mb-1">Memory Usage</div>
              <div className="text-xl text-blue-400">{stats.memory_mb.toFixed(2)} MB</div>
            </div>
            <div className="bg-white/5 p-3 rounded border border-white/10">
              <div className="text-[var(--muted)] mb-1">Artifacts Generated</div>
              <div className="text-xl text-purple-400">{stats.files} files</div>
            </div>
            <div className="bg-white/5 p-3 rounded border border-white/10">
              <div className="text-[var(--muted)] mb-1">Determinism</div>
              <div className="text-xl text-emerald-400">{stats.determinism_status}</div>
            </div>
          </div>
        )}
        {subTab === "tokens" && (
          <pre className="text-[var(--text)] whitespace-pre-wrap break-all">
            {JSON.stringify(tokens || [], null, 2)}
          </pre>
        )}
        {subTab === "ast" && (
          <pre className="text-[var(--text)]">
            {JSON.stringify(ast || {}, null, 2)}
          </pre>
        )}
        {subTab === "ir" && (
          <pre className="text-[var(--text)]">
            {JSON.stringify(module || {}, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
