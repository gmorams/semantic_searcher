import { useState } from "react";
import clsx from "clsx";
import { api } from "../lib/api";
import type { AskAllResponse, AskResponse, Mode } from "../types";
import { Sources } from "./Sources";
import { TechDetails } from "./TechDetails";

const MODE_LABELS: Record<Mode, string> = {
  bm25: "BM25",
  dense: "Vectorial",
  ontology: "Expansió ontològica",
  controlled: "Controlada (ontologia)",
  hybrid: "Híbrida (RRF)",
};
const MODES_ORDER: Mode[] = ["bm25", "dense", "ontology", "controlled", "hybrid"];

const SUGGESTIONS = [
  "Quan són els exàmens finals del GEI?",
  "Quantes assignatures té el semestre 3 del GEI?",
  "Quin és el codi UPC de PSD-GIA?",
  "Si faig el màster de ciència de dades, amb quins centres puc fer doble titulació?",
];

export function AllStrategiesPanel() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState<AskAllResponse | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<Mode>("hybrid");

  async function run(q?: string) {
    const query = (q ?? question).trim();
    if (!query || pending) return;
    setQuestion(query);
    setError(null);
    setPending(true);
    setResult(null);
    try {
      const res = await api.askAll(query, []);
      setResult(res);
      // Triar el primer mode amb resposta com a actiu (per defecte hybrid)
      const firstReady = MODES_ORDER.find((m) => res.responses[m]);
      if (firstReady) setActiveMode(firstReady);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error desconegut");
    } finally {
      setPending(false);
    }
  }

  const active = result?.responses[activeMode];
  const activeError = result?.errors?.[activeMode];

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        <div className="mx-auto flex max-w-4xl flex-col gap-4">
          <header className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
            <h2 className="text-base font-semibold text-upcblue">
              Resposta amb totes les estratègies
            </h2>
            <p className="mt-1 text-xs text-slate-500">
              Executa la mateixa pregunta amb els 5 modes de recuperació en paral·lel.
              Cada pestanya mostra la resposta de l'agent generada per aquell mode i
              les seves fonts.
            </p>
          </header>

          {!result && !pending && (
            <div className="mx-auto flex max-w-3xl flex-col items-center gap-3 pt-6 text-center">
              <p className="text-sm text-slate-600">
                Tria un exemple o escriu la teva pregunta a baix.
              </p>
              <div className="mt-2 flex flex-wrap justify-center gap-2">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    type="button"
                    onClick={() => run(s)}
                    className="btn-ghost border border-slate-200"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {pending && (
            <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
              Executant les 5 estratègies en paral·lel… (això pot trigar uns segons).
            </div>
          )}

          {error && (
            <div className="rounded-xl border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              {error}
            </div>
          )}

          {result && (
            <>
              <nav className="flex flex-wrap gap-1 border-b border-slate-200">
                {MODES_ORDER.map((m) => {
                  const hasResp = !!result.responses[m];
                  const isError = !!result.errors?.[m];
                  return (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setActiveMode(m)}
                      className={clsx(
                        "rounded-t-lg border border-b-0 px-3 py-1.5 text-xs font-medium",
                        activeMode === m
                          ? "border-slate-200 bg-white text-upcblue"
                          : "border-transparent bg-slate-100 text-slate-600 hover:bg-slate-50",
                        !hasResp && "italic text-slate-400",
                      )}
                      title={isError ? `Error: ${result.errors?.[m]}` : MODE_LABELS[m]}
                    >
                      {MODE_LABELS[m]}{isError ? " ⚠" : ""}
                    </button>
                  );
                })}
              </nav>

              {/* Selector alternatiu per a pantalles petites */}
              <div className="md:hidden">
                <label className="text-xs text-slate-500">Mode</label>
                <select
                  value={activeMode}
                  onChange={(e) => setActiveMode(e.target.value as Mode)}
                  className="ml-2 rounded border border-slate-300 px-2 py-1 text-xs"
                >
                  {MODES_ORDER.map((m) => (
                    <option key={m} value={m}>
                      {MODE_LABELS[m]}
                    </option>
                  ))}
                </select>
              </div>

              <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                <h3 className="mb-2 text-sm font-semibold text-upcblue">
                  {MODE_LABELS[activeMode]}
                </h3>
                {activeError && (
                  <div className="mb-2 rounded bg-red-50 px-3 py-2 text-xs text-red-700">
                    Aquest mode ha fallat: {activeError}
                  </div>
                )}
                {active && <AnswerView resp={active} />}
              </article>

              {/* Top-K per mode (recuperat dels resultats per cada estrategia) */}
              <details className="rounded-xl border border-slate-200 bg-slate-50 p-3">
                <summary className="cursor-pointer text-xs font-medium text-slate-700">
                  Mostra el top-K de pàgines retornades per cada estratègia
                </summary>
                <table className="mt-2 w-full border-collapse text-xs">
                  <thead>
                    <tr className="bg-white text-left">
                      <th className="border-b px-2 py-1 font-semibold">Estratègia</th>
                      <th className="border-b px-2 py-1 font-semibold">Top 1</th>
                      <th className="border-b px-2 py-1 font-semibold">Top 2</th>
                      <th className="border-b px-2 py-1 font-semibold">Top 3</th>
                    </tr>
                  </thead>
                  <tbody>
                    {MODES_ORDER.map((m) => {
                      const resp = result.responses[m];
                      const urls = resp?.sources?.slice(0, 3) ?? [];
                      return (
                        <tr key={m} className="bg-white/50">
                          <td className="border-b px-2 py-1 font-medium text-upcblue">
                            {MODE_LABELS[m]}
                          </td>
                          {[0, 1, 2].map((i) => (
                            <td key={i} className="max-w-xs truncate border-b px-2 py-1">
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
              </details>
            </>
          )}
        </div>
      </div>

      <div className="border-t border-slate-200 bg-white px-6 py-3">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            run();
          }}
          className="mx-auto flex max-w-3xl gap-2"
        >
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Pregunta'm i compararé les 5 estratègies…"
            disabled={pending}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-fibblue focus:outline-none"
          />
          <button type="submit" className="btn-primary" disabled={pending || !question.trim()}>
            {pending ? "Executant…" : "Executar"}
          </button>
        </form>
      </div>
    </div>
  );
}

function AnswerView({ resp }: { resp: AskResponse }) {
  return (
    <>
      <div className="whitespace-pre-wrap text-sm leading-relaxed text-slate-800">
        {resp.answer}
      </div>
      <Sources urls={resp.sources} />
      <TechDetails details={resp} />
    </>
  );
}
