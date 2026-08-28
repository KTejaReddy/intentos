import { ExternalLink, RefreshCw, X } from "lucide-react";
import { useStore } from "../../store/useStore";

export default function PreviewPanel() {
  const { previewUrl, setPreviewUrl, running, activeProject, console } = useStore();

  if (!previewUrl) return null;

  return (
    <aside className="w-[420px] shrink-0 flex flex-col glass-strong border-l border-white/5 animate-fadeIn">
      <div className="panel-header">
        <span>Preview</span>
        <div className="flex items-center gap-1">
          <button
            title="Reload"
            onClick={() => setPreviewUrl(previewUrl + (previewUrl.includes("?") ? "&_=" : "?_=") + Date.now())}
            className="p-1 rounded hover:bg-white/10"
          >
            <RefreshCw size={12} />
          </button>
          <button title="Open in new tab" onClick={() => window.open(previewUrl, "_blank")} className="p-1 rounded hover:bg-white/10">
            <ExternalLink size={12} />
          </button>
          <button onClick={() => setPreviewUrl(null)} className="p-1 rounded hover:bg-white/10">
            <X size={12} />
          </button>
        </div>
      </div>
      <div className="relative flex-1 min-h-0">
        {running && (
          <div className="absolute top-2 left-2 z-10 chip text-emerald-300 bg-emerald-500/15">● running</div>
        )}
        <iframe src={previewUrl} className="preview-frame" title="app preview" />
      </div>
      <div className="px-3 py-2 border-t border-white/5 text-[11px] text-[var(--muted)] flex items-center gap-2">
        <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
        standalone preview — no build required
        <span
          className="ml-auto text-indigo-300 cursor-pointer hover:underline"
          onClick={() => activeProject && useStore.getState().openFile("source/app.intentlang", "app.intentlang")}
        >
          open source
        </span>
      </div>
    </aside>
  );
}
