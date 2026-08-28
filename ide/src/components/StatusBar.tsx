import { GitBranch, Hammer, Play, CircleAlert, Loader2 } from "lucide-react";
import { useStore } from "../store/useStore";
import { api } from "../api/client";

export default function StatusBar() {
  const {
    activeProject, diagnostics, compiling, running, console, setCompiling,
    setBuildResult, setPreviewUrl, setRunning, gitItems, refreshProject,
    clearConsole,
  } = useStore();

  if (!activeProject) return null;

  const errors = diagnostics.filter((d) => d.severity === "error").length;
  const warnings = diagnostics.filter((d) => d.severity === "warning").length;

  const doBuild = async () => {
    if (!activeProject || compiling) return;
    setCompiling(true);
    clearConsole();
    console("step", `building project ${activeProject.name}…`);
    try {
      const res = await api.build(activeProject.id);
      setBuildResult(res);
      for (const s of res.steps || []) {
        console(s.ok ? "ok" : "error", `[${s.ok ? "ok" : "!!"}] ${s.name.padEnd(10)} ${s.elapsed_ms.toFixed(2)} ms  ${s.detail}`);
      }
      for (const d of (res.diagnostics || []) as any[]) {
        if (d.severity === "error") console("error", `${d.file}:${d.line}:${d.col} [${d.code}] ${d.message}`);
        else if (d.severity === "warning") console("info", `${d.file}:${d.line} [${d.code}] ${d.message}`);
      }
      console(res.ok ? "ok" : "error", res.ok
        ? `build complete — ${res.artifacts?.count ?? 0} artifacts, fingerprint ${res.fingerprint?.slice(0, 12)}…`
        : `build failed — ${(res.diagnostics || []).filter((d: any) => d.severity === "error").length} error(s)`);
      await refreshProject();
    } catch (e: any) {
      console("error", `build error: ${e.message}`);
    } finally {
      setCompiling(false);
    }
  };

  const doRun = async () => {
    if (!activeProject) return;
    await doBuild();
    setRunning(true);
    try {
      const res = await api.run(activeProject.id);
      setPreviewUrl(res.preview_url);
      console("ok", `running at ${res.preview_url}`);
    } catch (e: any) {
      console("error", `run error: ${e.message}`);
    }
  };

  return (
    <footer className="h-8 shrink-0 flex items-center gap-4 px-4 border-t border-white/5 bg-white/[0.02] text-[11px] text-[var(--muted)] select-none">
      <span className="flex items-center gap-1.5">
        <GitBranch size={12} /> {gitItems.length > 0 ? gitItems[0].path || "branch" : "no repo"}
      </span>
      <button onClick={() => useStore.setState({ bottomOpen: true, bottomTab: "problems" })} className="flex items-center gap-1.5 hover:text-[var(--text)]">
        {errors > 0 ? <CircleAlert size={12} className="text-rose-400" /> : <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />}
        {errors} errors · {warnings} warnings
      </button>

      <div className="flex-1" />

      <button
        onClick={doBuild}
        disabled={compiling}
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 border border-white/10 hover:bg-white/5 transition-colors disabled:opacity-50"
      >
        {compiling ? <Loader2 size={12} className="animate-spin" /> : <Hammer size={12} />}
        {compiling ? "Building…" : "Build"}
      </button>
      <button
        onClick={doRun}
        disabled={running || compiling}
        className="flex items-center gap-1.5 rounded-md px-2.5 py-1 bg-gradient-to-r from-indigo-500 to-violet-500 text-white hover:brightness-110 transition-all disabled:opacity-50"
      >
        <Play size={12} /> {running ? "Running…" : "Run"}
      </button>
    </footer>
  );
}
