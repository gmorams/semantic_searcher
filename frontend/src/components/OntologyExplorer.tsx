import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { OntologyClass, OntologyConcept } from "../types";

export function OntologyExplorer() {
  const [classes, setClasses] = useState<OntologyClass[]>([]);
  const [selectedClass, setSelectedClass] = useState<string>("");
  const [instances, setInstances] = useState<OntologyConcept[]>([]);
  const [selected, setSelected] = useState<OntologyConcept | null>(null);

  useEffect(() => {
    api.ontologyClasses().then((cs) => {
      setClasses(cs);
      if (cs.length > 0) setSelectedClass(cs[0].name);
    });
  }, []);

  useEffect(() => {
    if (!selectedClass) return;
    api.ontologyInstances(selectedClass).then(setInstances);
    setSelected(null);
  }, [selectedClass]);

  return (
    <div className="space-y-3">
      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Classe OWL
        </label>
        <select
          value={selectedClass}
          onChange={(e) => setSelectedClass(e.target.value)}
          className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
        >
          {classes.map((c) => (
            <option key={c.name} value={c.name}>
              {c.name} ({c.instance_count})
            </option>
          ))}
        </select>
      </div>

      <div>
        <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-slate-500">
          Instància
        </label>
        <select
          value={selected?.label ?? ""}
          onChange={(e) => {
            const lab = e.target.value;
            if (!lab) {
              setSelected(null);
              return;
            }
            api.ontologyInstance(lab).then(setSelected);
          }}
          className="w-full rounded-lg border border-slate-200 bg-white px-2 py-1.5 text-sm"
        >
          <option value="">— Selecciona —</option>
          {instances.map((i) => (
            <option key={i.label} value={i.label}>
              {i.label}
            </option>
          ))}
        </select>
      </div>

      {selected && (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
          {selected.code && (
            <div className="mb-1">
              <span className="text-xs font-semibold uppercase text-slate-500">Codi:</span>{" "}
              <code className="text-fibblue">{selected.code}</code>
            </div>
          )}
          {selected.synonyms.length > 0 && (
            <div className="mb-2">
              <div className="text-xs font-semibold uppercase text-slate-500">
                Etiquetes SKOS
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {selected.synonyms.slice(0, 8).map((s) => (
                  <span key={s} className="badge">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {selected.related.length > 0 && (
            <div className="mb-2">
              <div className="text-xs font-semibold uppercase text-slate-500">
                skos:related
              </div>
              <div className="mt-1 flex flex-wrap gap-1">
                {selected.related.map((s) => (
                  <span key={s} className="badge">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
          {selected.url && (
            <div className="mb-1 text-xs">
              <span className="font-semibold uppercase text-slate-500">Recurs canònic: </span>
              <a
                href={selected.url}
                target="_blank"
                rel="noreferrer"
                className="text-fibblue hover:underline"
              >
                {selected.url.split("/ca/").slice(-1)[0]}
              </a>
            </div>
          )}
          {selected.weight !== null && selected.type === "Concepte acadèmic" && (
            <div className="text-xs text-slate-500">
              Pes d'intenció: <code>{selected.weight.toFixed(2)}</code>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
