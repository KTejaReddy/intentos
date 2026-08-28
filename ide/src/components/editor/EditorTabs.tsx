import { X } from "lucide-react";
import { useStore } from "../../store/useStore";

export default function EditorTabs() {
  const { tabs, activeTab, dirty, openFile, closeTab, projectFiles, fileContents } = useStore();

  const syncTab = async (path: string, name: string) => {
    // ensure content loaded when tab is created from the file tree
    if (fileContents[path] === undefined) await openFile(path, name);
    else useStore.setState({ activeTab: path });
  };

  return (
    <div className="h-9 shrink-0 flex items-stretch border-b border-white/5 bg-white/[0.02] overflow-x-auto">
      {tabs.length === 0 && (
        <div className="flex items-center px-4 text-[12px] text-[var(--muted)]">
          {projectFiles.length === 0
            ? "No files — build the project to generate source"
            : "Open a file from the explorer"}
        </div>
      )}
      {tabs.map((tab) => (
        <div
          key={tab.path}
          onClick={() => syncTab(tab.path, tab.name)}
          className={`group flex items-center gap-2 pl-3 pr-1.5 text-[12px] border-r border-white/5 cursor-pointer select-none transition-colors ${
            activeTab === tab.path
              ? "bg-[#0b0f1a] text-[var(--text)]"
              : "text-[var(--muted)] hover:bg-white/5"
          }`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-indigo-400" />
          <span className="whitespace-nowrap">{tab.name}</span>
          {dirty[tab.path] && <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />}
          <button
            onClick={(e) => {
              e.stopPropagation();
              closeTab(tab.path);
            }}
            className="p-1 rounded hover:bg-white/10 opacity-0 group-hover:opacity-100"
          >
            <X size={12} />
          </button>
        </div>
      ))}
    </div>
  );
}
