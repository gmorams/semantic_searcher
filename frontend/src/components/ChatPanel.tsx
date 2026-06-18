import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import type { Message, Mode } from "../types";
import { MessageBubble } from "./MessageBubble";

interface Props {
  mode: Mode;
}

const SUGGESTIONS = [
  "Com funciona la matrícula al grau d'informàtica?",
  "Quines especialitats té el GEI?",
  "Què s'estudia a XC?",
  "Quan són els exàmens finals?",
  "Vull anar d'Erasmus",
];

export function ChatPanel({ mode }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, pending]);

  async function send(question: string) {
    if (!question.trim() || pending) return;
    setError(null);
    const userMsg: Message = { role: "user", content: question };
    const history = messages;
    setMessages([...history, userMsg]);
    setInput("");
    setPending(true);
    try {
      const res = await api.ask(question, mode, history);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: res.answer, details: res },
      ]);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Error desconegut";
      setError(msg);
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: `No s'ha pogut completar la consulta (${msg}).`,
        },
      ]);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 ? (
          <EmptyState onPick={send} />
        ) : (
          <div className="mx-auto flex max-w-3xl flex-col gap-4">
            {messages.map((m, i) => (
              <MessageBubble key={i} message={m} />
            ))}
            {pending && (
              <div className="text-sm italic text-slate-500">Cercant amb {mode}…</div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </div>

      <div className="border-t border-slate-200 bg-white px-6 py-3">
        {error && (
          <div className="mb-2 rounded-md bg-red-50 px-3 py-2 text-xs text-red-700">
            {error}
          </div>
        )}
        <form
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
          className="mx-auto flex max-w-3xl gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Fes una pregunta sobre la FIB…"
            disabled={pending}
            className="flex-1 rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-fibblue focus:outline-none"
          />
          <button type="submit" className="btn-primary" disabled={pending || !input.trim()}>
            Enviar
          </button>
        </form>
      </div>
    </div>
  );
}

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="mx-auto flex max-w-3xl flex-col items-center gap-4 pt-10 text-center">
      <h2 className="text-xl font-semibold text-upcblue">Demana qualsevol cosa de la FIB</h2>
      <p className="text-sm text-slate-500">
        Tràmits, assignatures, calendari, intercanvis, professors… amb fonts citades.
      </p>
      <div className="mt-4 flex flex-wrap justify-center gap-2">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => onPick(s)}
            className="btn-ghost border border-slate-200"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
