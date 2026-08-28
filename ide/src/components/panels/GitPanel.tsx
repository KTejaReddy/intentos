import { GitBranch, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

export default function GitPanel() {
  const { activeProject, gitItems, gitDiff, setGit } = useStore();
  const [tab, setTab] = useState<"status" | "diff" | "log">("status");
  const [log, setLog] = useState<any[]>([]);

  useEffect(() => {
    if (!activeProject) return;
    let alive = true;
    api.gitStatus(activeProject.id).then((d) => alive && setGit(d.items || [], "")).catch(() => {});
    api.gitDiff(activeProject.id).then((d) => alive && setGit(gitItems, d.diff || "")).catch(() => {});
    api.gitLog(activeProject.id).then((d) => alive && setLog(d.commits || [])).catch(() => {});
    return () => {
      alive = false;
    };
  }, [activeProject?.id]);

  if (!activeProject) return null;

  const refresh = async () => {
    const [s, d, l] = await Promise.all([
      api.gitStatus(activeProject.id).catch(() => ({ items: [] })),
      api.gitDiff(activeProject.id).catch(() => ({ diff: "" })),
      api.gitLog(activeProject.id).catch(() => ({ commits: [] })),
    ]);
    setGit(s.items || [], d.diff || "");
    setLog(l.commits || []);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">
        <span>Source Control</span>
        <button onClick={refresh} className="p-1 rounded hover:bg-white/10">
          <RefreshCw size={12} />
        </button>
      </div>
      <div className="flex gap-1 p-2">
        {(["status", "diff", "log"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`flex-1 rounded-md py-1 text-[11px] font-medium capitalize transition-colors ${
              tab === t ? "bg-indigo-500/20 text-indigo-200" : "text-[var(--muted)] hover:bg-white/5"
            }`}
          >
            {t}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-4 text-[12px]">
        {tab === "status" &&
          (gitItems.length === 0 ? (
            <div className="text-center text-[var(--muted)] py-8">
              <GitBranch size={18} className="mx-auto mb-2 opacity-50" />
              Working tree clean
            </div>
          ) : (
            gitItems.map((item, i) => (
              <div key={i} className="flex items-center gap-2 px-2 py-1 rounded hover:bg-white/5">
                <span
                  className={`w-8 text-center rounded text-[10px] font-bold ${
                    item.status === "??" ? "bg-emerald-500/20 text-emerald-300" :
                    item.status.startsWith("M") ? "bg-amber-500/20 text-amber-300" :
                    item.status.startsWith("D") ? "bg-rose-500/20 text-rose-300" :
                    "bg-sky-500/20 text-sky-300"
                  }`}
                >
                  {item.status === "??" ? "U" : item.status[0]}
                </span>
                <span className="code-font truncate">{item.path}</span>
              </div>
            ))
          ))}
        {tab === "diff" && (
          <pre className="code-font text-[11px] whitespace-pre-wrap text-emerald-300/80 p-2">{gitDiff || "No unstaged changes"}</pre>
        )}
        {tab === "log" &&
          (log.length === 0 ? (
            <div className="text-center text-[var(--muted)] py-8">No commits</div>
          ) : (
            log.map((c, i) => (
              <div key={i} className="flex items-start gap-2 px-2 py-1.5 border-b border-white/5">
                <span className="code-font text-indigo-300">{c.hash}</span>
                <div className="min-w-0">
                  <div className="truncate">{c.subject}</div>
                  <div className="text-[10px] text-[var(--muted)]">{c.author}</div>
                </div>
              </div>
            ))
          ))}
      </div>
    </div>
  );
}
