import { Database, Table, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { useStore } from "../../store/useStore";
import { api } from "../../api/client";

export default function DbViewer() {
  const { activeProject, tables, selectedTable, setTables, setSelectedTable, console } = useStore();
  const [rows, setRows] = useState<{ columns: string[]; rows: any[][] } | null>(null);

  useEffect(() => {
    if (activeProject) {
      api.dbTables(activeProject.id).then((d) => setTables(d.tables || [])).catch(() => {});
    }
  }, [activeProject?.id]);

  const loadTable = async (name: string) => {
    if (!activeProject) return;
    setSelectedTable(name);
    const d = await api.dbTable(activeProject.id, name);
    setRows(d);
  };

  if (!activeProject) return null;

  return (
    <div className="flex flex-col h-full">
      <div className="panel-header">
        <span>Database</span>
        <button
          title="Refresh"
          onClick={() => api.dbTables(activeProject.id).then((d) => setTables(d.tables || [])).catch(() => {})}
          className="p-1 rounded hover:bg-white/10"
        >
          <RefreshCw size={12} />
        </button>
      </div>

      <div className="px-3 py-2 text-[12px] text-[var(--muted)]">Runtime SQLite (applied from schema.sql)</div>

      <div className="px-2 flex-1 overflow-y-auto">
        {tables.length === 0 && (
          <div className="text-center text-[12px] text-[var(--muted)] py-8">
            <Database size={20} className="mx-auto mb-2 opacity-50" />
            No tables yet.
            <br />
            Build the project to apply the schema.
          </div>
        )}
        {tables.map((t) => (
          <div
            key={t.name}
            onClick={() => loadTable(t.name)}
            className={`tree-row justify-between ${selectedTable === t.name ? "active" : ""}`}
          >
            <span className="flex items-center gap-1.5">
              <Table size={13} className="text-emerald-300" />
              {t.name}
            </span>
            <span className="text-[10px] text-[var(--muted)]">{t.rows} rows</span>
          </div>
        ))}
      </div>

      {selectedTable && (
        <div className="border-t border-white/5">
          <div className="panel-header">
            <span className="code-font normal-case">{selectedTable}</span>
            <span className="text-[10px]">{rows?.rows.length ?? 0} rows</span>
          </div>
          <div className="overflow-auto max-h-56">
            {rows && rows.columns.length > 0 ? (
              <table className="w-full text-[11px]">
                <thead>
                  <tr className="text-left text-[var(--muted)] border-b border-white/10">
                    {rows.columns.map((c) => (
                      <th key={c} className="px-2 py-1 font-medium">{c}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.rows.map((r, i) => (
                    <tr key={i} className="border-b border-white/5 hover:bg-white/5">
                      {r.map((cell, j) => (
                        <td key={j} className="px-2 py-1 code-font truncate max-w-[140px]">
                          {String(cell ?? "NULL")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="text-[11px] text-[var(--muted)] p-3">Empty table</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
