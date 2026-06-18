import { useState } from "react";
import clsx from "clsx";
import type { AskResponse } from "../types";

interface Props {
  details: AskResponse;
}

type Tab = "search" | "ontology" | "api" | "docs";

export function TechDetails({ details }: Props) {
  const [tab, setTab] = useState<Tab>("search");

  return (
    <details className="mt-2 rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700">
        🔬 Detalls tècnics
      </summary>
      <div className="border-t border-slate-100 px-3 py-3">
        <div className="mb-3 flex gap-2 text-xs">
          <TabButton active={tab === "search"} onClick={() => setTab("search")}>
            Cerca
          </TabButton>
          <TabButton active={tab === "ontology"} onClick={() => setTab("ontology")}>
            Ontologia
          </TabButton>
          <TabButton active={tab === "api"} onClick={() => setTab("api")}>
            API FIB
          </TabButton>
          <TabButton active={tab === "docs"} onClick={() => setTab("docs")}>
            Documents ({details.retrieved_docs.length})
          </TabButton>
        </div>

        {tab === "search" && (
          <div className="space-y-2 text-sm">
            <Row label="Mode" value={<code>{details.mode}</code>} />
            <Row label="Query condensada" value={details.search_question} />
            <Row label="Query enriquida" value={<code>{details.enriched_query}</code>} />
            {details.entities.length > 0 && (
              <Row
                label="Entitats enllaçades"
                value={
                  <ul className="space-y-0.5">
                    {details.entities.map(([label, url]) => (
                      <li key={url}>
                        <code>{label}</code> →{" "}
                        <a
                          href={url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-fibblue hover:underline"
                        >
                          {url.split("/ca/").slice(-1)[0]}
                        </a>
                      </li>
                    ))}
                  </ul>
                }
              />
            )}
          </div>
        )}

        {tab === "ontology" && (
          <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-700">
            {details.ontology_context || "Cap concepte ontològic detectat."}
          </pre>
        )}

        {tab === "api" && (
          <pre className="overflow-x-auto whitespace-pre-wrap rounded bg-slate-50 p-3 text-xs text-slate-700">
            {details.api_context || "L'API FIB no ha aportat dades estructurades per aquesta consulta."}
          </pre>
        )}

        {tab === "docs" && (
          <ul className="space-y-3">
            {details.retrieved_docs.map((d) => (
              <li key={`${d.rank}-${d.source}`} className="border-b border-slate-100 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-medium">{d.title || "(sense títol)"}</span>
                  <span className="badge">score {d.score.toFixed(3)}</span>
                  {d.boosts.map((b) => (
                    <span key={b} className="badge-boost">
                      {b}
                    </span>
                  ))}
                </div>
                <p className="mt-1 text-xs text-slate-600">{d.preview}</p>
                <a
                  href={d.source}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1 inline-block text-xs text-fibblue hover:underline"
                >
                  {d.source}
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </details>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        "rounded-md px-2 py-1 font-medium transition",
        active ? "bg-fibblue text-white" : "bg-slate-100 text-slate-600 hover:bg-slate-200",
      )}
    >
      {children}
    </button>
  );
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[140px_1fr] gap-2">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div>{value}</div>
    </div>
  );
}
