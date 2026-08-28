import { File, FileCode, Folder, FolderOpen, RefreshCw, X } from "lucide-react";
import { useState } from "react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

export default function Explorer() {
  const { activeProject, projectFiles, openFile, tabs, closeTab, refreshProject, fileContents, dirty } = useStore();
  const [openDirs, setOpenDirs] = useState<Record<string, boolean>>({});

  if (!activeProject) return null;

  const tree = useTree(projectFiles.map((f) => f.path));

  const toggleDir = (key: string) => setOpenDirs((s) => ({ ...s, [key]: !s[key] }));

  const save = async (path: string) => {
    if (!activeProject) return;
    try {
      await api.writeFile(activeProject.id, path, fileContents[path] ?? "");
      useStore.setState((s) => ({ dirty: { ...s.dirty, [path]: false } }));
      refreshProject();
    } catch (e: any) {
      alert(e.message);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">
        <span>Explorer</span>
        <div className="flex items-center gap-1">
          <button title="Refresh" onClick={refreshProject} className="p-1 rounded hover:bg-white/10">
            <RefreshCw size={12} />
          </button>
          <button title="Close project" onClick={() => useStore.getState().closeProject()} className="p-1 rounded hover:bg-white/10">
            <X size={12} />
          </button>
        </div>
      </div>

      <div className="px-3 py-2 text-[12px] text-[var(--muted)] truncate">
        {activeProject.name}
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {tree.map((node) => (
          <TreeBranch
            key={node.path}
            node={node}
            depth={0}
            openDirs={openDirs}
            toggleDir={toggleDir}
            onOpen={openFile}
            dirty={dirty}
            onSave={save}
          />
        ))}
        {tree.length === 0 && (
          <div className="text-[12px] text-[var(--muted)] px-2 py-4 text-center">
            No source files yet.
            <br />
            Run <b>Build</b> to generate the app.
          </div>
        )}
      </div>

      {tabs.length > 0 && (
        <div className="border-t border-white/5 p-2">
          <div className="text-[10px] uppercase tracking-wider text-[var(--muted)] mb-1 px-1">Open editors</div>
          {tabs.map((t) => (
            <div key={t.path} className="tree-row justify-between group">
              <span className="flex items-center gap-1.5 truncate" onClick={() => openFile(t.path, t.name)}>
                <FileCode size={13} className="text-indigo-300 shrink-0" />
                <span className="truncate">{t.name}</span>
                {dirty[t.path] && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />}
              </span>
              <span className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
                <button onClick={() => save(t.path)} className="p-0.5 rounded hover:bg-white/10 text-[10px]">save</button>
                <button onClick={() => closeTab(t.path)} className="p-0.5 rounded hover:bg-white/10">✕</button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface TreeNode {
  name: string;
  path: string;
  isDir: boolean;
  children: TreeNode[];
}

function useTree(paths: string[]): TreeNode[] {
  const root: TreeNode[] = [];
  const lookup = new Map<string, TreeNode>();
  const mk = (name: string, path: string, isDir: boolean): TreeNode => {
    const node = { name, path, isDir, children: [] };
    lookup.set(path, node);
    return node;
  };
  for (const p of paths.sort()) {
    const parts = p.split("/");
    let current: TreeNode[] = root;
    let acc = "";
    parts.forEach((part, i) => {
      acc = acc ? `${acc}/${part}` : part;
      const isLast = i === parts.length - 1;
      let node = lookup.get(acc);
      if (!node) {
        node = mk(part, acc, !isLast);
        current.push(node);
      }
      current = node.children;
    });
  }
  return root;
}

function TreeBranch({
  node, depth, openDirs, toggleDir, onOpen, dirty, onSave,
}: {
  node: TreeNode;
  depth: number;
  openDirs: Record<string, boolean>;
  toggleDir: (k: string) => void;
  onOpen: (path: string, name: string) => void;
  dirty: Record<string, boolean>;
  onSave: (path: string) => void;
}) {
  if (node.isDir) {
    const open = openDirs[node.path];
    return (
      <div>
        <div
          className="tree-row"
          style={{ paddingLeft: 8 + depth * 12 }}
          onClick={() => toggleDir(node.path)}
        >
          {open ? <FolderOpen size={14} className="text-indigo-300" /> : <Folder size={14} className="text-indigo-300" />}
          <span>{node.name}</span>
        </div>
        {open &&
          node.children.map((child) => (
            <TreeBranch
              key={child.path}
              node={child}
              depth={depth + 1}
              openDirs={openDirs}
              toggleDir={toggleDir}
              onOpen={onOpen}
              dirty={dirty}
              onSave={onSave}
            />
          ))}
      </div>
    );
  }
  const name = node.name.split(".").pop() || "";
  return (
    <div
      className="tree-row group justify-between"
      style={{ paddingLeft: 8 + depth * 12 }}
      onClick={() => onOpen(node.path, node.name)}
      onDoubleClick={() => onSave(node.path)}
    >
      <span className="flex items-center gap-1.5 truncate">
        <File size={14} className="text-[var(--muted)] shrink-0" />
        <span className="truncate">{node.name}</span>
        {dirty[node.path] && <span className="w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0" />}
      </span>
      <span className="text-[10px] text-[var(--muted)] opacity-0 group-hover:opacity-100">{name}</span>
    </div>
  );
}
