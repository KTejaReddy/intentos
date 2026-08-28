import { Bot, Send, User, Sparkles, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

const SUGGESTIONS = [
  "Explain how IntentLang becomes an application",
  "Add a payment flow to my app in IntentLang",
  "What's missing from my current design?",
  "Show me the IntentLang for a reviews feature",
];

export default function ChatPanel() {
  const { chatMessages, pushChat, chatStreaming, setChatStreaming, setChatOpen, activeProject } = useStore();
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatMessages, chatStreaming]);

  const send = async (text?: string) => {
    const content = (text ?? input).trim();
    if (!content || chatStreaming) return;
    setInput("");
    pushChat({ role: "user", content });
    pushChat({ role: "assistant", content: "" });
    setChatStreaming(true);
    try {
      const res = await api.chat([...chatMessages, { role: "user", content }], activeProject?.id);
      if (!res.body) throw new Error("no stream");
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
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
          if (data.text !== undefined) {
            useStore.setState((s) => {
              const msgs = [...s.chatMessages];
              const last = msgs[msgs.length - 1];
              msgs[msgs.length - 1] = { ...last, content: last.content + data.text };
              return { chatMessages: msgs };
            });
          }
        }
      }
    } catch (e: any) {
      pushChat({ role: "assistant", content: `⚠️ ${e.message}` });
    } finally {
      setChatStreaming(false);
    }
  };

  return (
    <aside className="w-[340px] shrink-0 flex flex-col glass-strong border-l border-white/5 animate-fadeIn">
      <div className="panel-header">
        <span className="flex items-center gap-1.5">
          <Bot size={13} className="text-indigo-300" /> AI Assistant
        </span>
        <button onClick={() => setChatOpen(false)} className="p-1 rounded hover:bg-white/10">
          <X size={12} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {chatMessages.length === 0 && (
          <div className="text-center pt-6">
            <Sparkles size={22} className="mx-auto mb-2 text-indigo-300" />
            <p className="text-[12px] text-[var(--muted)] leading-relaxed">
              Ask about your IntentLang program, architecture, or what to build next.
            </p>
            <div className="mt-4 space-y-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="block w-full text-left glass rounded-lg px-3 py-2 text-[12px] hover:border-indigo-400/40 transition-colors"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {chatMessages.map((m, i) => (
          <div key={i} className={`flex gap-2 animate-fadeUp ${m.role === "user" ? "flex-row-reverse" : ""}`}>
            <div
              className={`w-6 h-6 rounded-full grid place-items-center shrink-0 ${
                m.role === "user" ? "bg-emerald-500/25 text-emerald-300" : "bg-indigo-500/25 text-indigo-300"
              }`}
            >
              {m.role === "user" ? <User size={12} /> : <Bot size={12} />}
            </div>
            <div
              className={`max-w-[85%] rounded-xl px-3 py-2 text-[13px] leading-relaxed whitespace-pre-wrap ${
                m.role === "user"
                  ? "bg-indigo-500/20 border border-indigo-400/20"
                  : "bg-white/5 border border-white/5"
              }`}
            >
              {m.content}
              {m.role === "assistant" && i === chatMessages.length - 1 && chatStreaming && (
                <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-indigo-300 animate-pulse align-middle" />
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="p-3 border-t border-white/5">
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="Ask about your app…"
            className="flex-1 rounded-lg bg-white/5 border border-white/10 px-3 py-2 text-[13px] outline-none focus:border-indigo-400/50 transition-colors"
          />
          <button
            onClick={() => send()}
            disabled={chatStreaming || !input.trim()}
            className="btn btn-primary !px-3 !py-2 disabled:opacity-40"
          >
            <Send size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
