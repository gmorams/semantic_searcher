"""Baseline 2: cerca lexica BM25 (Okapi BM25 sobre els chunks indexats).

El corpus es carrega una sola vegada des de ChromaDB i es tokenitza amb
normalitzacio (minuscules, sense accents) i stopwords ca/es minimes.
"""

import re

from rank_bm25 import BM25Okapi

from db.vector_store import VectorStore
from ontology.fib_ontology import normalize
from retrieval.base import BaseRetriever, make_item
from utils import SingletonMeta
import settings

STOPWORDS = {
    # catala
    "el", "la", "els", "les", "un", "una", "uns", "unes", "de", "del", "dels",
    "a", "al", "als", "i", "o", "en", "per", "amb", "que", "es", "som", "son",
    "com", "quins", "quines", "quin", "quina", "on", "quan", "qui", "hi", "ha",
    "puc", "vull", "fer", "te", "tinc", "meu", "meva", "aquest", "aquesta",
    # castella
    "los", "las", "y", "u", "se", "su", "para", "con", "por", "donde", "cuando",
    "cual", "cuales", "quiero", "puedo", "hay", "este", "esta", "mi", "tengo",
}


class BM25Retriever(BaseRetriever, metaclass=SingletonMeta):
    name = "bm25"
    description = "Cerca lexica BM25 (baseline)"

    def __init__(self):
        self.vector_store = VectorStore()
        self._load_corpus()

    def _tokenize(self, text):
        tokens = re.findall(r"[a-z0-9]+", normalize(text))
        return [t for t in tokens if t not in STOPWORDS and len(t) > 1]

    def _load_corpus(self):
        collection = self.vector_store.collection
        data = collection.get(include=["documents", "metadatas"])
        self.documents = data.get("documents") or []
        self.metadatas = data.get("metadatas") or []
        tokenized = []
        for doc, meta in zip(self.documents, self.metadatas):
            # El titol i la seccio tambe aporten senyal lexica
            text = f"{meta.get('title', '')} {meta.get('section', '')} {doc}"
            tokenized.append(self._tokenize(text))
        self.bm25 = BM25Okapi(tokenized) if tokenized else None

    def search(self, query, top_k=None):
        top_k = top_k or settings.TOP_K
        results = []
        if self.bm25:
            scores = self.bm25.get_scores(self._tokenize(query))
            ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            max_score = scores[ranked[0]] if len(ranked) and scores[ranked[0]] > 0 else 1.0
            for rank, idx in enumerate(ranked[:top_k], start=1):
                if scores[idx] <= 0:
                    break
                item = make_item(
                    self.documents[idx],
                    self.metadatas[idx],
                    scores[idx] / max_score,  # normalitzat a [0,1] per a la UI
                    "bm25",
                    rank,
                )
                results.append(item)
        return {
            "query": query,
            "enriched_query": query,
            "ontology_context": "",
            "entities": [],
            "results": results,
        }
