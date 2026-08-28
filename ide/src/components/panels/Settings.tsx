import { useEffect, useState } from "react";
import { Save, KeyRound, Server, Cpu, Rocket } from "lucide-react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

export default function SettingsPanel() {
  const { setProvider, console } = useStore();
  const [form, setForm] = useState<any>({});

  useEffect(() => {
    api.getSettings().then(setForm).catch(() => {});
  }, []);

  const set = (k: string, v: string) => setForm((s: any) => ({ ...s, [k]: v }));

  const save = async () => {
    try {
      const saved = await api.putSettings(form);
      setForm(saved);
      setProvider(saved.provider || "offline");
      console("ok", `settings saved — provider: ${saved.provider}`);
    } catch (e: any) {
      console("error", `settings save failed: ${e.message}`);
    }
  };

  const Field = ({ label, icon: Icon, k, placeholder, type = "text" }: any) => (
    <label className="block mb-3">
      <span className="flex items-center gap-1.5 text-[12px] text-[var(--muted)] mb-1">
        <Icon size={12} /> {label}
      </span>
      <input
        type={type}
        value={form[k] ?? ""}
        onChange={(e) => set(k, e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-[13px] outline-none focus:border-indigo-400/50 transition-colors"
      />
    </label>
  );

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">
        <span>Settings</span>
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <label className="block mb-4">
          <span className="flex items-center gap-1.5 text-[12px] text-[var(--muted)] mb-1">
            <Rocket size={12} /> AI Provider
          </span>
          <select
            value={form.provider ?? "offline"}
            onChange={(e) => set("provider", e.target.value)}
            className="w-full rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-[13px] outline-none focus:border-indigo-400/50"
          >
            <option value="offline">Offline (deterministic planner — no API key)</option>
            <option value="openrouter">OpenRouter (qwen, deepseek, …)</option>
            <option value="ollama">Ollama (local — qwen2.5)</option>
          </select>
        </label>

        {form.provider === "openrouter" && (
          <>
            <Field label="OpenRouter API Key" icon={KeyRound} k="api_key" type="password" placeholder="sk-or-…" />
            <Field label="Model" icon={Cpu} k="openrouter_model" placeholder="qwen/qwen-2.5-72b-instruct" />
          </>
        )}
        {form.provider === "ollama" && (
          <>
            <Field label="Ollama Base URL" icon={Server} k="base_url" placeholder="http://localhost:11434" />
            <Field label="Model" icon={Cpu} k="model" placeholder="qwen2.5:7b" />
          </>
        )}

        <div className="glass rounded-xl p-3 text-[12px] text-[var(--muted)] leading-relaxed mb-4">
          <b className="text-[var(--text)]">AI policy</b>: the AI planner writes <b>IntentLang only</b>.
          Production code is always produced by the IntentLang compiler — never by the model.
          Without a key, IntentOS runs fully offline with the deterministic heuristic planner.
        </div>

        <button onClick={save} className="btn btn-primary w-full">
          <Save size={14} /> Save settings
        </button>
      </div>
    </div>
  );
}
