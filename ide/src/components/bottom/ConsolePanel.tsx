import { Trash2, Terminal } from "lucide-react";
import { useEffect, useRef } from "react";
import { useStore } from "../../store/useStore";

export default function ConsolePanel() {
  const { consoleLines, clearConsole, bottomTab } = useStore();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight });
  }, [consoleLines]);

  if (bottomTab !== "console") return null;

  return (
    <div className="h-full flex flex-col">
      <div className="panel-header">
        <span className="flex items-center gap-1.5">
          <Terminal size={12} /> Compiler Console
        </span>
        <button onClick={clearConsole} className="p-1 rounded hover:bg-white/10">
          <Trash2 size={12} />
        </button>
      </div>
      <div ref={ref} className="flex-1 overflow-y-auto py-1">
        {consoleLines.length === 0 && (
          <div className="console-line console-muted">
            IntentOS compiler console — press Build to compile the project.
          </div>
        )}
        {consoleLines.map((line, i) => (
          <div key={i} className={`console-line console-${line.kind}`}>
            {line.kind === "step" && <span className="text-indigo-300">▸ </span>}
            {line.text}
          </div>
        ))}
      </div>
    </div>
  );
}
