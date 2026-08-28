import { File, Folder, Hammer } from "lucide-react";
import { useStore } from "../../store/useStore";

export default function OutputPanel() {
  const { buildResult, bottomTab } = useStore();
  if (bottomTab !== "output") return null;

  const files = buildResult?.artifacts?.files || [];

  return (
    <div className="h-full overflow-y-auto py-1">
      {files.length === 0 && (
        <div className="console-line console-muted">
          <Hammer size={12} className="inline mr-1" />
          No build output — press Build in the status bar.
        </div>
      )}
      {files.map((f: { path: string; note?: string }, i: number) => {
        const depth = f.path.split("/").length;
        const isDir = f.path.includes("/");
        return (
          <div key={i} className="flex items-center gap-2 px-3 py-0.5 text-[12px] hover:bg-white/5 code-font">
            <span style={{ paddingLeft: (depth - 1) * 12 }} />
            {isDir ? (
              <Folder size={12} className="text-indigo-300 shrink-0" />
            ) : (
              <File size={12} className="text-[var(--muted)] shrink-0" />
            )}
            <span className="truncate">{f.path}</span>
            {f.note && (
              <span className="ml-auto text-[10px] text-[var(--muted)] shrink-0">{f.note}</span>
            )}
          </div>
        );
      })}
    </div>
  );
}
