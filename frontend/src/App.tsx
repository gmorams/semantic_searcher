import { useEffect, useState } from "react";
import clsx from "clsx";
import { api } from "./lib/api";
import { ChatPanel } from "./components/ChatPanel";
import { Comparator } from "./components/Comparator";
import { Sidebar } from "./components/Sidebar";
import { AllStrategiesPanel } from "./components/AllStrategiesPanel";
import type { Mode, Stats } from "./types";

type View = "chat" | "all";

export default function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [mode, setMode] = useState<Mode>("hybrid");
  const [view, setView] = useState<View>("chat");
  const [bootError, setBootError] = useState<string | null>(null);

  useEffect(() => {
    api
      .stats()
      .then((s) => setStats(s))
      .catch((e) => setBootError(e instanceof Error ? e.message : "Error desconegut"));
  }, []);

  if (bootError) {
    return (
      <div className="flex h-full items-center justify-center p-6">
        <div className="max-w-md rounded-xl border border-red-200 bg-white p-6 shadow-sm">
          <h1 className="text-lg font-semibold text-red-700">No s'ha pogut connectar amb l'API</h1>
          <p className="mt-2 text-sm text-slate-700">{bootError}</p>
          <p className="mt-3 text-xs text-slate-500">
            Comprova que el backend FastAPI estigui en marxa a{" "}
            <code>http://localhost:8000</code> i que <code>chroma_db/</code> estigui indexat.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      <Sidebar stats={stats} mode={mode} onModeChange={setMode} />
      <div className="flex h-full flex-1 flex-col">
        <header className="border-b border-slate-200 bg-gradient-to-r from-upcblue to-fibblue px-6 py-3 text-white">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-base font-semibold">SemanticFIB</h1>
              <p className="text-xs opacity-80">
                {view === "chat" ? (
                  <>Buscador semàntic de la FIB · Mode actiu: <b>{mode}</b></>
                ) : (
                  <>Buscador semàntic de la FIB · Execució paral·lela de les 5 estratègies</>
                )}
              </p>
            </div>
            <nav className="flex gap-1 rounded-lg bg-white/10 p-1 text-xs">
              <TopTab active={view === "chat"} onClick={() => setView("chat")}>
                Chat (mode únic)
              </TopTab>
              <TopTab active={view === "all"} onClick={() => setView("all")}>
                Totes les estratègies
              </TopTab>
            </nav>
          </div>
        </header>
        <main className="flex-1 overflow-hidden">
          {view === "chat" ? <ChatPanel mode={mode} /> : <AllStrategiesPanel />}
        </main>
        {view === "chat" && <Comparator />}
      </div>
    </div>
  );
}

function TopTab({
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
        "rounded-md px-3 py-1.5 font-medium transition",
        active ? "bg-white text-upcblue" : "text-white/80 hover:bg-white/10",
      )}
    >
      {children}
    </button>
  );
}
