import type { Mode, Stats } from "../types";
import { ModeSelector } from "./ModeSelector";
import { OntologyExplorer } from "./OntologyExplorer";

interface Props {
  stats: Stats | null;
  mode: Mode;
  onModeChange: (m: Mode) => void;
}

export function Sidebar({ stats, mode, onModeChange }: Props) {
  return (
    <aside className="flex h-full w-80 shrink-0 flex-col gap-5 overflow-y-auto border-r border-slate-200 bg-white px-4 py-5">
      <header>
        <h1 className="text-lg font-semibold text-upcblue">SemanticFIB</h1>
        <p className="text-xs text-slate-500">Buscador semàntic · Ontologia + RAG</p>
      </header>

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Estratègia de cerca
        </h2>
        {stats ? (
          <ModeSelector modes={stats.available_modes} value={mode} onChange={onModeChange} />
        ) : (
          <p className="text-sm text-slate-400">Carregant…</p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Índex
        </h2>
        {stats ? (
          <div className="grid grid-cols-3 gap-2 text-center">
            <Metric label="Frag." value={stats.document_count} />
            <Metric label="Triples" value={stats.ontology_triples} />
            <Metric label="Instàn." value={stats.ontology_instances} />
          </div>
        ) : (
          <p className="text-sm text-slate-400">…</p>
        )}
      </section>

      <section>
        <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Ontologia del domini
        </h2>
        <OntologyExplorer />
      </section>

      <footer className="mt-auto border-t border-slate-100 pt-3 text-xs text-slate-400">
        <p>TFG · Giancarlo Morales</p>
        <p>UPC · FIB · Dir. Ramon Sangüesa</p>
      </footer>
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg bg-slate-50 px-2 py-1.5">
      <div className="text-sm font-semibold text-upcblue">{value}</div>
      <div className="text-[10px] uppercase tracking-wide text-slate-500">{label}</div>
    </div>
  );
}
