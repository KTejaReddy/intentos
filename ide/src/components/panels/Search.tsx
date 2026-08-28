import { Search as SearchIcon, X } from "lucide-react";
import { useMemo, useState } from "react";
import { useStore } from "../../store/useStore";

export default function SearchPanel() {
  const { fileContents } = useStore();
  const [query, setQuery] = useState("");

  const results = useMemo(() => {
    if (!query.trim()) return [];
    const q = query.toLowerCase();
    const hits: { path: string; line: number; text: string }[] = [];
    for (const [path, content] of Object.entries(fileContents)) {
      content.split("\n").forEach((line, i) => {
        if (line.toLowerCase().includes(q)) {
          hits.push({ path, line: i + 1, text: line.trim().slice(0, 120) });
        }
      });
    }
    return hits.slice(0, 100);
  }, [query, fileContents]);

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">Search</div>
      <div className="p-3">
        <div className="relative">
          <SearchIcon size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-[var(--muted)]" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search open files…"
            className="w-full rounded-lg bg-white/5 border border-white/10 pl-8 pr-3 py-1.5 text-[13px] outline-none focus:border-indigo-400/50 transition-colors"
          />
          {query && (
            <button onClick={() => setQuery("")} className="absolute right-2 top-1/2 -translate-y-1/2 text-[var(--muted)] hover:text-white">
              <X size={13} />
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {results.map((r, i) => (
          <div key={i} className="px-2 py-1.5 rounded-md hover:bg-white/5 cursor-pointer text-[12px]">
            <div className="flex gap-2 text-[var(--muted)]">
              <span className="text-indigo-300 truncate">{r.path}</span>
              <span>:{r.line}</span>
            </div>
            <div className="code-font text-[var(--text)]/90 truncate">{r.text}</div>
          </div>
        ))}
        {query && results.length === 0 && (
          <div className="text-[12px] text-[var(--muted)] text-center py-6">No matches</div>
        )}
      </div>
    </div>
  );
}
