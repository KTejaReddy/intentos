import { Boxes, CloudOff, Cloud, Zap } from "lucide-react";
import { useStore } from "../store/useStore";

export default function TitleBar() {
  const { online, provider, activeProject } = useStore();
  return (
    <header className="h-10 shrink-0 flex items-center gap-3 px-4 border-b border-white/5 bg-white/[0.02] select-none">
      <div className="flex items-center gap-2">
        <div className="w-6 h-6 rounded-md bg-gradient-to-br from-indigo-500 to-emerald-400 grid place-items-center shadow-glow">
          <Boxes size={14} className="text-white" />
        </div>
        <span className="font-bold tracking-tight text-[14px]">
          Intent<span className="gradient-text">OS</span>
        </span>
        <span className="chip ml-1 text-[10px] opacity-70">
          AI Development Operating System
        </span>
      </div>

      <div className="flex-1" />

      {activeProject && (
        <span className="text-[12px] text-[var(--muted)] truncate max-w-[260px]">
          {activeProject.name}
        </span>
      )}

      <div className="flex items-center gap-2">
        {online ? (
          <span className="chip text-emerald-300/90 border-emerald-400/20">
            <Cloud size={11} /> backend online
          </span>
        ) : (
          <span className="chip text-rose-300/90 border-rose-400/20">
            <CloudOff size={11} /> backend offline
          </span>
        )}
        <span className="chip">
          <Zap size={11} className="text-amber-300" /> {provider}
        </span>
      </div>
    </header>
  );
}
