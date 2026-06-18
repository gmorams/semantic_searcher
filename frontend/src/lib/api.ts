import type {
  AskAllResponse,
  AskResponse,
  CompareResponse,
  Message,
  Mode,
  OntologyClass,
  OntologyConcept,
  Stats,
} from "../types";

const BASE = (import.meta.env.VITE_API_BASE ?? "/api/v1").replace(/\/$/, "");

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  stats: () => http<Stats>("/stats"),
  health: () => http<{ status: string; version: string }>("/health"),

  ask: (question: string, mode: Mode, history: Message[]) =>
    http<AskResponse>("/ask", {
      method: "POST",
      body: JSON.stringify({
        question,
        mode,
        history: history.map(({ role, content }) => ({ role, content })),
      }),
    }),

  compare: (query: string, top_k_per_mode = 3) =>
    http<CompareResponse>("/compare", {
      method: "POST",
      body: JSON.stringify({ query, top_k_per_mode }),
    }),

  askAll: (question: string, history: Message[] = []) =>
    http<AskAllResponse>("/ask-all", {
      method: "POST",
      body: JSON.stringify({
        question,
        history: history.map(({ role, content }) => ({ role, content })),
      }),
    }),

  ontologyClasses: () => http<OntologyClass[]>("/ontology/classes"),
  ontologyInstances: (cls: string) =>
    http<OntologyConcept[]>(`/ontology/instances?cls=${encodeURIComponent(cls)}`),
  ontologyInstance: (label: string) =>
    http<OntologyConcept>(`/ontology/instance/${encodeURIComponent(label)}`),
};
