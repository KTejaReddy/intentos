import { Check, Loader2, XCircle, Bot, FileCode2, Cpu, Rocket, Search, ListChecks, Hammer } from "lucide-react";
import { useStore } from "../../store/useStore";

const STEP_META: Record<string, { label: string; icon: any; desc: string }> = {
  intent: { label: "Analyze intent", icon: Search, desc: "English → structured intent" },
  requirements: { label: "Requirements", icon: ListChecks, desc: "missing features surfaced" },
  plan: { label: "Product plan", icon: Bot, desc: "spec: entities, users, features" },
  intentlang: { label: "Generate IntentLang", icon: FileCode2, desc: "deterministic program" },
  compile: { label: "Compile", icon: Cpu, desc: "lexer → parser → IR → codegen" },
  project: { label: "Materialize project", icon: Rocket, desc: "workspace + preview ready" },
};

export default function PipelineStepper() {
  const { pipelineSteps, pipelineRunning } = useStore();

  const stepMap = new Map(pipelineSteps.map((s) => [s.name, s]));

  return (
    <div className="w-[380px] glass-strong rounded-2xl p-5 animate-fadeUp">
      <div className="flex items-center gap-2 mb-4">
        <Hammer size={16} className="text-indigo-300" />
        <h3 className="font-semibold text-[14px]">IntentOS pipeline</h3>
        {pipelineRunning && (
          <span className="chip text-indigo-300 bg-indigo-500/15 animate-pulseGlow">running</span>
        )}
      </div>

      <div className="space-y-0">
        {Object.entries(STEP_META).map(([id, meta], i) => {
          const step = stepMap.get(id);
          const Icon = meta.icon;
          const status = step?.status ?? (pipelineRunning ? "running" : "pending");
          const active = status === "running";
          return (
            <div key={id}>
              <div className="flex items-start gap-3">
                <div className="flex flex-col items-center">
                  <div
                    className={`w-7 h-7 rounded-full grid place-items-center border transition-all duration-300 ${
                      status === "done"
                        ? "bg-emerald-500/20 border-emerald-400/50 text-emerald-300"
                        : active
                        ? "bg-indigo-500/20 border-indigo-400/60 text-indigo-300 animate-pulseGlow"
                        : status === "error"
                        ? "bg-rose-500/20 border-rose-400/50 text-rose-300"
                        : "bg-white/5 border-white/10 text-[var(--muted)]"
                    }`}
                  >
                    {status === "done" ? (
                      <Check size={13} />
                    ) : active ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : status === "error" ? (
                      <XCircle size={13} />
                    ) : (
                      <Icon size={13} />
                    )}
                  </div>
                  {i < Object.keys(STEP_META).length - 1 && (
                    <div className="step-connector" />
                  )}
                </div>
                <div className="pb-5 min-w-0">
                  <div className="text-[13px] font-medium flex items-center gap-2">
                    {meta.label}
                    {step?.detail && (
                      <span className="text-[10px] text-[var(--muted)] font-normal truncate">
                        {step.detail}
                      </span>
                    )}
                  </div>
                  <div className="text-[11px] text-[var(--muted)]">{meta.desc}</div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
