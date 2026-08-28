import { Plug, ExternalLink } from "lucide-react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

export default function PluginsPanel() {
  const { plugins, togglePlugin, console } = useStore();

  const toggle = async (id: string, enabled: boolean) => {
    try {
      await api.togglePlugin(id);
      togglePlugin(id);
      console("ok", `plugin '${id}' ${enabled ? "enabled" : "disabled"} — rebuild to regenerate`);
    } catch (e: any) {
      console("error", `plugin toggle failed: ${e.message}`);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">
        <span>Plugin Marketplace</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        <div className="chip text-[10px]">
          <Plug size={11} /> plugins extend the compiler with new code generators
        </div>
        {plugins.map((p) => (
          <div key={p.id} className="glass rounded-xl p-3 animate-fadeUp">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500/40 to-violet-500/40 grid place-items-center">
                  <Plug size={13} />
                </span>
                <div>
                  <div className="text-[13px] font-semibold">{p.name}</div>
                  <div className="text-[10px] text-[var(--muted)]">
                    {p.type} · v{p.version} · {p.author}
                  </div>
                </div>
              </div>
              <button
                onClick={() => toggle(p.id, p.enabled)}
                className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${
                  p.enabled ? "bg-indigo-500" : "bg-white/10"
                }`}
              >
                <span
                  className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all duration-200 ${
                    p.enabled ? "left-[18px]" : "left-0.5"
                  }`}
                />
              </button>
            </div>
            <p className="text-[12px] text-[var(--muted)] leading-relaxed">{p.description}</p>
            <div className="mt-2 flex items-center gap-2 text-[11px]">
              {p.enabled ? (
                <span className="chip text-emerald-300 border-emerald-400/20">enabled · `Use {p.id}` in IntentLang</span>
              ) : (
                <span className="chip">disabled</span>
              )}
              <ExternalLink size={10} className="opacity-40" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
