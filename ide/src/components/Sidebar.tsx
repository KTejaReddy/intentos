import { useStore } from "../store/useStore";
import Explorer from "./panels/Explorer";
import SearchPanel from "./panels/Search";
import GitPanel from "./panels/GitPanel";
import DbViewer from "./panels/DbViewer";
import PluginsPanel from "./panels/Plugins";
import SettingsPanel from "./panels/Settings";

export default function Sidebar() {
  const { activity } = useStore();
  if (!activity) return null;
  return (
    <aside className="w-60 shrink-0 border-r border-white/5 bg-white/[0.015] glass flex flex-col overflow-hidden animate-fadeIn">
      {activity === "explorer" && <Explorer />}
      {activity === "search" && <SearchPanel />}
      {activity === "git" && <GitPanel />}
      {activity === "db" && <DbViewer />}
      {activity === "plugins" && <PluginsPanel />}
      {activity === "settings" && <SettingsPanel />}
    </aside>
  );
}
