import { useState } from "react";
import { ArrowRight, Boxes, Sparkles, Wand2, Cpu, FileCode2 } from "lucide-react";
import { useStore } from "../../store/useStore";
import PipelineStepper from "./PipelineStepper";

const EXAMPLES = [
  "Create a food delivery startup for Hyderabad",
  "Build a student portal for a college",
  "A task tracker for small teams with notifications",
  "An e-commerce marketplace for handmade goods",
];

export default function Onboarding() {
  const { idea, setIdea, setOnboarding, setPipelineSteps, setPipelineRunning, console, openProject } = useStore();
  const [error, setError] = useState<string | null>(null);
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");

  const run = async (ideaText?: string) => {
    const text = (ideaText ?? idea).trim();
    if (!text || phase === "running") return;
    setIdea(text);
    setError(null);
    setPhase("running");
    setPipelineSteps([]);
    setPipelineRunning(true);
    console("step", `pipeline start — "${text}"`);

    try {
      const res = await fetch("/api/pipeline/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ idea: text }),
      });
      if (!res.body) throw new Error("no response stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      let result: any = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop() || "";
        for (const evt of events) {
          const dataLine = evt.split("\n").find((l) => l.startsWith("data:"));
          if (!dataLine) continue;
          const data = JSON.parse(dataLine.slice(5));
          if (data.name) {
            useStore.setState((s) => ({ pipelineSteps: [...s.pipelineSteps, data] }));
            const mark = data.status === "done" ? "ok" : data.status === "error" ? "error" : "info";
            console(mark as any, `[${data.name}] ${data.status} — ${data.detail}`);
          } else if (data.result) {
            result = data.result;
          } else if (data.message) {
            throw new Error(data.message);
          }
        }
      }
      if (!result?.project_id) throw new Error("pipeline did not produce a project");
      console("ok", `project ${result.project_id} ready — opening workspace…`);

      const projects = await fetch("/api/projects").then((r) => r.json());
      useStore.setState({ projects });
      const project = projects.find((p: any) => p.id === result.project_id);
      if (project) await openProject(project);
      setPhase("done");
      setOnboarding(false);
    } catch (e: any) {
      setError(e.message);
      console("error", `pipeline failed: ${e.message}`);
      setPhase("idle");
    } finally {
      setPipelineRunning(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto">
      <div className="min-h-full flex items-center justify-center p-8">
        <div className="w-full max-w-4xl grid grid-cols-1 md:grid-cols-[1fr_auto] gap-10 items-center">
          <div className="animate-fadeUp">
            <div className="flex items-center gap-3 mb-6">
              <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-emerald-400 grid place-items-center shadow-glow">
                <Boxes size={24} className="text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-extrabold tracking-tight">
                  Intent<span className="gradient-text">OS</span>
                </h1>
                <p className="text-[13px] text-[var(--muted)]">
                  The AI Development Operating System
                </p>
              </div>
            </div>

            <h2 className="text-2xl font-bold leading-snug mb-2">
              Describe your software idea.
              <br />
              <span className="gradient-text">We compile it into an application.</span>
            </h2>

            <div className="flex items-center gap-2 text-[12px] text-[var(--muted)] mb-6 flex-wrap">
              <span className="chip"><Wand2 size={11} /> AI Planner</span>
              <ArrowRight size={11} />
              <span className="chip"><FileCode2 size={11} /> IntentLang</span>
              <ArrowRight size={11} />
              <span className="chip"><Cpu size={11} /> Compiler</span>
              <ArrowRight size={11} />
              <span className="chip"><Sparkles size={11} /> Application</span>
            </div>

            <div className="glass-strong rounded-2xl p-3">
              <textarea
                value={idea}
                onChange={(e) => setIdea(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && run()}
                placeholder='"Create a food delivery startup for Hyderabad"'
                rows={3}
                className="w-full bg-transparent outline-none resize-none text-[15px] placeholder:text-[var(--muted)]/60 leading-relaxed"
              />
              <div className="flex items-center justify-between gap-3">
                <div className="flex gap-1.5 flex-wrap">
                  {EXAMPLES.map((ex) => (
                    <button
                      key={ex}
                      onClick={() => setIdea(ex)}
                      className="text-[11px] px-2.5 py-1 rounded-full border border-white/10 text-[var(--muted)] hover:text-[var(--text)] hover:border-indigo-400/40 transition-colors"
                    >
                      {ex}
                    </button>
                  ))}
                </div>
                <button
                  onClick={() => run()}
                  disabled={phase === "running" || !idea.trim()}
                  className="btn btn-primary shrink-0 disabled:opacity-40"
                >
                  {phase === "running" ? "Compiling…" : "Generate app"}
                  <ArrowRight size={15} />
                </button>
              </div>
            </div>

            {error && (
              <div className="mt-3 chip text-rose-300 border-rose-400/30">{error}</div>
            )}

            <div className="mt-6 grid grid-cols-3 gap-3 text-center">
              {[
                ["100%", "deterministic compilation"],
                ["0", "lines of AI-written code"],
                ["1", "language to describe any app"],
              ].map(([n, label]) => (
                <div key={label} className="glass rounded-xl py-3 px-2">
                  <div className="text-xl font-extrabold gradient-text">{n}</div>
                  <div className="text-[10px] text-[var(--muted)] leading-tight mt-1">{label}</div>
                </div>
              ))}
            </div>
          </div>

          {(phase === "running" || phase === "done") && <PipelineStepper />}
        </div>
      </div>
    </div>
  );
}
