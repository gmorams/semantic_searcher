import { useState } from "react";
import { api } from "../lib/api";
import type { CompareResponse, Mode } from "../types";

const MODE_LABELS: Record<Mode, string> = {
  bm25: "BM25",
  dense: "Vectorial",
  ontology: "Expansió",
  controlled: "Controlada",
  hybrid: "Híbrida (RRF)",
};

export function Comparator() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<CompareResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    if (!query.trim() || pending) return;
    setPending(true);
    setError(null);
    try {
      const res = await api.compare(query, 3);
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconegut");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="border-t border-slate-200 bg-slate-50 px-6 py-4">
      <details className="mx-auto max-w-5xl">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">
          ⚖️ Comparador d'estratègies (executa la consulta amb les 5 estratègies alhora)
        </summary>
        <div className="mt-3 flex gap-2">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="p. ex. Quan són els exàmens finals?"
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm"
          />
          <button onClick={run} disabled={!query.trim() || pending} className="btn-primary">
            {pending ? "Comparant…" : "Comparar"}
          </button>
        </div>

        {error && <div className="mt-2 text-xs text-red-700">{error}</div>}

        {result && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full border-collapse text-sm">
              <thead>
                <tr className="bg-white text-left">
                  <th className="border-b px-3 py-2 font-semibold">Estratègia</th>
                  <th className="border-b px-3 py-2 font-semibold">Top 1</th>
                  <th className="border-b px-3 py-2 font-semibold">Top 2</th>
                  <th className="border-b px-3 py-2 font-semibold">Top 3</th>
                </tr>
              </thead>
              <tbody>
                {(Object.keys(MODE_LABELS) as Mode[]).map((m) => {
                  const urls = result.modes[m] ?? [];
                  return (
                    <tr key={m} className="bg-white/50">
                      <td className="border-b px-3 py-2 font-medium text-upcblue">
                        {MODE_LABELS[m]}
                      </td>
                      {[0, 1, 2].map((i) => (
                        <td key={i} className="max-w-xs truncate border-b px-3 py-2 text-xs">
                          {urls[i] ? (
                            <a
                              href={urls[i]}
                              target="_blank"
                              rel="noreferrer"
                              className="text-fibblue hover:underline"
                            >
                              {urls[i].split("/ca/").slice(-1)[0]}
                            </a>
                          ) : (
                            "—"
                          )}
                        </td>
                      ))}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </details>
    </section>
  );
}
