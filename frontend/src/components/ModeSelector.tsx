import clsx from "clsx";
import type { Mode } from "../types";

interface Props {
  modes: Record<string, string>;
  value: Mode;
  onChange: (mode: Mode) => void;
}

const MODE_LABELS: Record<Mode, string> = {
  hybrid: "Híbrida (RRF)",
  controlled: "Ontologia controlada + entity linking",
  ontology: "Expansió ontològica naive",
  dense: "Vectorial pura (baseline)",
  bm25: "Lèxica BM25 (baseline)",
};

export function ModeSelector({ modes, value, onChange }: Props) {
  const keys = (Object.keys(MODE_LABELS) as Mode[]).filter((k) => k in modes);

  return (
    <div className="space-y-1">
      {keys.map((mode) => {
        const active = mode === value;
        return (
          <button
            key={mode}
            type="button"
            onClick={() => onChange(mode)}
            className={clsx(
              "block w-full rounded-lg border px-3 py-2 text-left text-sm transition",
              active
                ? "border-fibblue bg-fibblue/5 text-upcblue"
                : "border-slate-200 bg-white text-slate-700 hover:bg-slate-50",
            )}
          >
            <div className="font-medium">{MODE_LABELS[mode]}</div>
            <div className="mt-0.5 text-xs text-slate-500">{modes[mode]}</div>
          </button>
        );
      })}
    </div>
  );
}
