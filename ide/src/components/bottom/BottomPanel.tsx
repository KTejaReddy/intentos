import { AlertTriangle, ChevronDown, FileOutput, Terminal, X } from "lucide-react";
import { useStore } from "../../store/useStore";
import ProblemsPanel from "./ProblemsPanel";
import OutputPanel from "./OutputPanel";
import ConsolePanel from "./ConsolePanel";
import PipelineVisualizer from "./PipelineVisualizer";

export default function BottomPanel() {
  const { bottomOpen, bottomTab, setBottomTab, toggleBottom, diagnostics } = useStore();
  if (!bottomOpen) return null;

  const errors = diagnostics.filter((d) => d.severity === "error").length;

  const tabs = [
    { id: "problems", icon: AlertTriangle, label: `Problems${errors ? ` (${errors})` : ""}` },
    { id: "output", icon: FileOutput, label: "Output" },
    { id: "console", icon: Terminal, label: "Console" },
    { id: "pipeline", icon: FileOutput, label: "Pipeline" },
  ] as const;

  return (
    <div className="h-44 shrink-0 border-t border-white/5 bg-white/[0.02] glass flex flex-col animate-fadeUp">
      <div className="flex items-center h-8 border-b border-white/5 px-2 gap-1 select-none">
        {tabs.map(({ id, icon: Icon, label }) => (
          <button
            key={id}
            onClick={() => setBottomTab(id)}
            className={`flex items-center gap-1.5 px-3 h-full text-[11px] font-medium transition-colors ${
              bottomTab === id ? "text-[var(--text)] border-b-2 border-indigo-400" : "text-[var(--muted)] hover:text-[var(--text)]"
            }`}
          >
            <Icon size={12} />
            {label}
          </button>
        ))}
        <div className="flex-1" />
        <button onClick={toggleBottom} className="p-1 rounded hover:bg-white/10 text-[var(--muted)]">
          <ChevronDown size={14} />
        </button>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">
        <ProblemsPanel />
        <OutputPanel />
        <ConsolePanel />
        <PipelineVisualizer />
      </div>
    </div>
  );
}
