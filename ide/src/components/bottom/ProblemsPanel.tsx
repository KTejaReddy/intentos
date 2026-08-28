import { CircleAlert, CircleX, Info } from "lucide-react";
import { useStore } from "../../store/useStore";

export default function ProblemsPanel() {
  const { diagnostics, bottomTab, openFile, activeTab } = useStore();

  if (bottomTab !== "problems") return null;

  const errors = diagnostics.filter((d) => d.severity === "error");
  const warnings = diagnostics.filter((d) => d.severity === "warning");
  const infos = diagnostics.filter((d) => d.severity === "info");

  const jump = (d: any) => {
    if (!activeTab) return;
    // Monaco marker jump handled via markers; here we just surface the line.
  };

  const Row = ({ d }: { d: any }) => (
    <div className="flex items-start gap-2 px-3 py-0.5 text-[12px] hover:bg-white/5 cursor-pointer" onClick={() => jump(d)}>
      {d.severity === "error" ? (
        <CircleX size={13} className="text-rose-400 shrink-0 mt-0.5" />
      ) : d.severity === "warning" ? (
        <CircleAlert size={13} className="text-amber-400 shrink-0 mt-0.5" />
      ) : (
        <Info size={13} className="text-sky-400 shrink-0 mt-0.5" />
      )}
      <span className="code-font text-[var(--muted)] shrink-0">
        {d.file}:{d.line}:{d.col}
      </span>
      <span className="truncate">
        <span className={`font-medium ${d.severity === "error" ? "text-rose-300" : d.severity === "warning" ? "text-amber-300" : "text-sky-300"}`}>
          [{d.code}]
        </span>{" "}
        {d.message}
      </span>
    </div>
  );

  return (
    <div className="h-full overflow-y-auto py-1">
      {errors.length + warnings.length + infos.length === 0 && (
        <div className="console-line console-muted">No problems detected.</div>
      )}
      {errors.map((d, i) => <Row key={`e${i}`} d={d} />)}
      {warnings.map((d, i) => <Row key={`w${i}`} d={d} />)}
      {infos.map((d, i) => <Row key={`i${i}`} d={d} />)}
    </div>
  );
}
