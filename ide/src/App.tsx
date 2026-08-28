import { useEffect } from "react";
import { useStore } from "./store/useStore";
import TitleBar from "./components/TitleBar";
import ActivityBar from "./components/ActivityBar";
import Sidebar from "./components/Sidebar";
import StatusBar from "./components/StatusBar";
import EditorTabs from "./components/editor/EditorTabs";
import EditorPane from "./components/editor/EditorPane";
import BottomPanel from "./components/bottom/BottomPanel";
import ChatPanel from "./components/chat/ChatPanel";
import PreviewPanel from "./components/bottom/PreviewPanel";
import Onboarding from "./components/onboarding/Onboarding";

export default function App() {
  const { booted, onboarding, chatOpen, previewUrl } = useStore();

  useEffect(() => {
    useStore.getState().boot();
  }, []);

  if (!booted) {
    return (
      <div className="h-full grid place-items-center">
        <div className="w-64 shimmer h-3 rounded-full mb-4" />
        <div className="text-[13px] text-[var(--muted)] animate-pulse">booting IntentOS…</div>
      </div>
    );
  }

  if (onboarding) {
    return (
      <div className="h-full flex flex-col">
        <TitleBar />
        <Onboarding />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <TitleBar />
      <div className="flex-1 flex min-h-0">
        <ActivityBar />
        <Sidebar />
        <main className="flex-1 flex flex-col min-w-0">
          <EditorTabs />
          <div className="flex-1 flex min-h-0">
            <div className="flex-1 flex flex-col min-w-0">
              <EditorPane />
              <BottomPanel />
            </div>
            {previewUrl && <PreviewPanel />}
          </div>
        </main>
        {chatOpen && <ChatPanel />}
      </div>
      <StatusBar />
    </div>
  );
}
