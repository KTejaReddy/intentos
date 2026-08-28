import { create } from "zustand";
import type {
  Activity, BottomTab, ChatMessage, CompileResult, ConsoleLine, Diagnostic,
  PipelineStep, PluginInfo, Project, TableInfo, GitItem,
} from "../types";

interface Tab {
  path: string;
  name: string;
}

interface IntentOSState {
  // session
  booted: boolean;
  provider: string;
  online: boolean;

  // projects
  projects: Project[];
  activeProject: Project | null;
  projectFiles: { path: string; size: number }[];
  fileContents: Record<string, string>;

  // editor
  tabs: Tab[];
  activeTab: string | null;
  dirty: Record<string, boolean>;
  diagnostics: Diagnostic[];
  compiling: boolean;
  buildResult: CompileResult | null;

  // panels
  activity: Activity | null;
  bottomOpen: boolean;
  bottomTab: BottomTab;
  chatOpen: boolean;
  chatMessages: ChatMessage[];
  chatStreaming: boolean;
  consoleLines: ConsoleLine[];
  previewUrl: string | null;
  running: boolean;

  // db / git / plugins
  tables: TableInfo[];
  selectedTable: string | null;
  gitItems: GitItem[];
  gitDiff: string;
  plugins: PluginInfo[];

  // pipeline / onboarding
  onboarding: boolean;
  idea: string;
  pipelineSteps: PipelineStep[];
  pipelineRunning: boolean;

  // actions
  boot: () => Promise<void>;
  setProvider: (p: string) => void;
  setProjects: (p: Project[]) => void;
  openProject: (p: Project) => Promise<void>;
  closeProject: () => void;
  refreshProject: () => Promise<void>;
  openFile: (path: string, name: string) => Promise<void>;
  closeTab: (path: string) => void;
  setContent: (path: string, content: string) => void;
  setDiagnostics: (d: Diagnostic[]) => void;
  setCompiling: (b: boolean) => void;
  setBuildResult: (r: CompileResult | null) => void;
  setActivity: (a: Activity | null) => void;
  toggleBottom: () => void;
  setBottomTab: (t: BottomTab) => void;
  setChatOpen: (b: boolean) => void;
  pushChat: (m: ChatMessage) => void;
  setChatStreaming: (b: boolean) => void;
  console: (kind: ConsoleLine["kind"], text: string) => void;
  clearConsole: () => void;
  setPreviewUrl: (u: string | null) => void;
  setRunning: (b: boolean) => void;
  setTables: (t: TableInfo[]) => void;
  setSelectedTable: (t: string | null) => void;
  setGit: (items: GitItem[], diff: string) => void;
  setPlugins: (p: PluginInfo[]) => void;
  togglePlugin: (id: string) => void;
  setOnboarding: (b: boolean) => void;
  setIdea: (i: string) => void;
  setPipelineSteps: (s: PipelineStep[]) => void;
  setPipelineRunning: (b: boolean) => void;
}

export const useStore = create<IntentOSState>((set, get) => ({
  booted: false,
  provider: "offline",
  online: false,

  projects: [],
  activeProject: null,
  projectFiles: [],
  fileContents: {},

  tabs: [],
  activeTab: null,
  dirty: {},
  diagnostics: [],
  compiling: false,
  buildResult: null,

  activity: "explorer",
  bottomOpen: true,
  bottomTab: "problems",
  chatOpen: false,
  chatMessages: [],
  chatStreaming: false,
  consoleLines: [],
  previewUrl: null,
  running: false,

  tables: [],
  selectedTable: null,
  gitItems: [],
  gitDiff: "",
  plugins: [],

  onboarding: true,
  idea: "",
  pipelineSteps: [],
  pipelineRunning: false,

  boot: async () => {
    try {
      const [health, projects, plugins] = await Promise.all([
        fetch("/api/health").then((r) => r.json()),
        fetch("/api/projects").then((r) => r.json()),
        fetch("/api/plugins").then((r) => r.json()),
      ]);
      set({
        booted: true,
        online: true,
        provider: health?.provider || "offline",
        projects,
        plugins: plugins?.plugins || [],
        onboarding: projects.length === 0,
      });
      // Re-open the most recently created project so a reload never strands
      // the user on an empty workbench.
      if (projects.length > 0) {
        const last = projects[projects.length - 1];
        set({ activeProject: last, activity: "explorer" });
        await get().refreshProject();
      }
    } catch {
      set({ booted: true, online: false, onboarding: true });
    }
  },

  setProvider: (p) => set({ provider: p }),
  setProjects: (p) => set({ projects: p }),

  openProject: async (p) => {
    set({ activeProject: p, onboarding: false, activity: "explorer" });
    await get().refreshProject();
  },

  closeProject: () =>
    set({
      activeProject: null,
      projectFiles: [],
      fileContents: {},
      tabs: [],
      activeTab: null,
      previewUrl: null,
      tables: [],
      onboarding: true,
    }),

  refreshProject: async () => {
    const p = get().activeProject;
    if (!p) return;
    const [files, tables] = await Promise.all([
      fetch(`/api/projects/${p.id}/files`).then((r) => r.json()),
      fetch(`/api/projects/${p.id}/db/tables`).then((r) => r.json()).catch(() => ({ tables: [] })),
    ]);
    set({ projectFiles: files.files || [], tables: tables.tables || [] });
    // refresh git status if the workspace is a repo
    fetch(`/api/projects/${p.id}/git/status`)
      .then((r) => r.json())
      .then((d) => set({ gitItems: d.items || [] }))
      .catch(() => set({ gitItems: [] }));
  },

  openFile: async (path, name) => {
    const p = get().activeProject;
    if (!p) return;
    const tabs = get().tabs;
    if (!tabs.some((t) => t.path === path)) {
      tabs.push({ path, name });
      set({ tabs: [...tabs] });
    }
    set({ activeTab: path });
    if (get().fileContents[path] === undefined) {
      try {
        const res = await fetch(`/api/projects/${p.id}/file?path=${encodeURIComponent(path)}`);
        const data = await res.json();
        set((s) => ({ fileContents: { ...s.fileContents, [path]: data.content } }));
      } catch {
        set((s) => ({ fileContents: { ...s.fileContents, [path]: "" } }));
      }
    }
  },

  closeTab: (path) => {
    const tabs = get().tabs.filter((t) => t.path !== path);
    let activeTab = get().activeTab;
    if (activeTab === path) activeTab = tabs.length ? tabs[tabs.length - 1].path : null;
    set({ tabs, activeTab });
  },

  setContent: (path, content) =>
    set((s) => ({
      fileContents: { ...s.fileContents, [path]: content },
      dirty: { ...s.dirty, [path]: true },
    })),

  setDiagnostics: (d) => set({ diagnostics: d }),
  setCompiling: (b) => set({ compiling: b }),
  setBuildResult: (r) => set({ buildResult: r }),
  setActivity: (a) => set({ activity: a }),
  toggleBottom: () => set((s) => ({ bottomOpen: !s.bottomOpen })),
  setBottomTab: (t) => set({ bottomTab: t }),
  setChatOpen: (b) => set({ chatOpen: b }),
  pushChat: (m) => set((s) => ({ chatMessages: [...s.chatMessages, m] })),
  setChatStreaming: (b) => set({ chatStreaming: b }),
  console: (kind, text) =>
    set((s) => ({ consoleLines: [...s.consoleLines.slice(-400), { kind, text, ts: Date.now() }] })),
  clearConsole: () => set({ consoleLines: [] }),
  setPreviewUrl: (u) => set({ previewUrl: u }),
  setRunning: (b) => set({ running: b }),
  setTables: (t) => set({ tables: t }),
  setSelectedTable: (t) => set({ selectedTable: t }),
  setGit: (items, diff) => set({ gitItems: items, gitDiff: diff }),
  setPlugins: (p) => set({ plugins: p }),
  togglePlugin: (id) =>
    set((s) => ({
      plugins: s.plugins.map((p) => (p.id === id ? { ...p, enabled: !p.enabled } : p)),
    })),
  setOnboarding: (b) => set({ onboarding: b }),
  setIdea: (i) => set({ idea: i }),
  setPipelineSteps: (s) => set({ pipelineSteps: s }),
  setPipelineRunning: (b) => set({ pipelineRunning: b }),
}));
