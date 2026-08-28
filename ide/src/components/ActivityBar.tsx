import {
  Database, FolderTree, Plug, Search, Settings, GitBranch, Bot,
} from "lucide-react";
import type { Activity } from "../types";
import { useStore } from "../store/useStore";

const ITEMS: { id: Activity | "chat"; icon: typeof FolderTree; label: string }[] = [
  { id: "explorer", icon: FolderTree, label: "Explorer" },
  { id: "search", icon: Search, label: "Search" },
  { id: "git", icon: GitBranch, label: "Git" },
  { id: "db", icon: Database, label: "Database" },
  { id: "plugins", icon: Plug, label: "Plugins" },
  { id: "chat", icon: Bot, label: "AI Chat" },
  { id: "settings", icon: Settings, label: "Settings" },
];

export default function ActivityBar() {
  const { activity, setActivity, chatOpen, setChatOpen, activeProject } = useStore();

  const activate = (id: Activity | "chat") => {
    if (id === "chat") {
      setChatOpen(!chatOpen);
      return;
    }
    setActivity(activity === id ? null : id);
  };

  return (
    <nav className="w-12 shrink-0 border-r border-white/5 bg-white/[0.02] glass flex flex-col items-center py-2 gap-1 select-none">
      {ITEMS.map(({ id, icon: Icon, label }) => {
        const active = id === "chat" ? chatOpen : activity === id;
        return (
          <button
            key={id}
            title={label}
            onClick={() => activate(id)}
            className={`relative w-10 h-10 grid place-items-center rounded-lg transition-all duration-150 ${
              active
                ? "text-indigo-300 bg-indigo-500/15"
                : "text-[var(--muted)] hover:text-[var(--text)] hover:bg-white/5"
            }`}
          >
            {active && (
              <span className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-full bg-gradient-to-b from-indigo-400 to-violet-500" />
            )}
            <Icon size={19} />
            {id === "chat" && <span className="absolute top-1 right-1 w-1.5 h-1.5 rounded-full bg-emerald-400" />}
          </button>
        );
      })}
      <div className="flex-1" />
      {activeProject && (
        <span className="text-[9px] text-[var(--muted)] uppercase tracking-widest">
          {activeProject.name.slice(0, 5)}
        </span>
      )}
      <span className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-emerald-400 grid place-items-center text-[10px] font-bold text-white mt-2">
        OS
      </span>
    </nav>
  );
}
