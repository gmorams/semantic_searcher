export type Mode = "bm25" | "dense" | "ontology" | "controlled" | "hybrid";

export interface Message {
  role: "user" | "assistant";
  content: string;
  details?: AskResponse;
}

export interface RetrievedDoc {
  rank: number;
  title: string;
  section: string;
  source: string;
  preview: string;
  score: number;
  similarity: number;
  retrieval_source: string;
  boosts: string[];
}

export interface AskResponse {
  answer: string;
  mode: Mode;
  sources: string[];
  search_question: string;
  enriched_query: string;
  ontology_context: string | null;
  api_context: string | null;
  entities: [string, string][];
  num_docs_retrieved: number;
  retrieved_docs: RetrievedDoc[];
}

export interface AskAllResponse {
  question: string;
  responses: Partial<Record<Mode, AskResponse>>;
  errors: Partial<Record<Mode, string>>;
}

export interface Stats {
  document_count: number;
  ontology_triples: number;
  ontology_instances: number;
  ontology_classes: number;
  instances_by_type: Record<string, number>;
  available_modes: Record<Mode, string>;
}

export interface OntologyClass {
  name: string;
  instance_count: number;
}

export interface OntologyConcept {
  label: string;
  type: string;
  code: string | null;
  url: string | null;
  synonyms: string[];
  related: string[];
  weight: number | null;
}

export interface CompareResponse {
  query: string;
  modes: Record<Mode, string[]>;
}
