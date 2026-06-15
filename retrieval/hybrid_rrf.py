"""EXP.3: cerca hibrida amb fusio Reciprocal Rank Fusion (RRF).

Fusiona les llistes rankejades de tres estrategies complementaries:
  - BM25 (precisio lexica: codis, noms exactes),
  - vectorial pura (cobertura semantica),
  - controlada per ontologia (coneixement de domini).

La fusio es fa a nivell de pagina (URL normalitzada):
    score(url) = sum_s  w_s / (k + rank_s(url))
amb k=60 (valor estandard de la literatura) i pesos configurables a settings.
"""

from collections import defaultdict

from retrieval.base import BaseRetriever, normalize_url
from retrieval.bm25 import BM25Retriever
from retrieval.controlled_ontology import ControlledOntologyRetriever
from retrieval.dense import DenseRetriever
import settings


class HybridRRFRetriever(BaseRetriever):
    name = "hybrid"
    description = "Fusio RRF de BM25 + vectorial + ontologia controlada"

    def __init__(self):
        self.dense = DenseRetriever()
        self.bm25 = BM25Retriever()
        self.controlled = ControlledOntologyRetriever()
        self.rrf_k = settings.RRF_K
        self.weights = {
            "controlled": settings.RRF_WEIGHT_CONTROLLED,
            "bm25": settings.RRF_WEIGHT_BM25,
            "dense": settings.RRF_WEIGHT_DENSE,
        }

    def search(self, query, top_k=None):
        top_k = top_k or settings.TOP_K
        candidate_k = settings.CANDIDATE_K

        controlled_out = self.controlled.search(query, top_k=candidate_k)
        runs = [
            ("controlled", controlled_out["results"]),
            ("bm25", self.bm25.search(query, top_k=candidate_k)["results"]),
            ("dense", self.dense.search(query, top_k=candidate_k)["results"]),
        ]

        rrf_scores = defaultdict(float)
        best_item = {}
        contributors = defaultdict(list)

        for run_name, results in runs:
            weight = self.weights[run_name]
            for rank, item in enumerate(results, start=1):
                url = normalize_url(item["source"])
                if not url:
                    continue
                rrf_scores[url] += weight / (self.rrf_k + rank)
                contributors[url].append(f"{run_name}@{rank}")
                if url not in best_item or item["similarity"] > best_item[url]["similarity"]:
                    best_item[url] = item

        ranked_urls = sorted(rrf_scores.items(), key=lambda kv: kv[1], reverse=True)

        merged = []
        for rank, (url, score) in enumerate(ranked_urls[:top_k], start=1):
            item = dict(best_item[url])
            item["rank"] = rank
            item["score"] = round(score, 6)
            item["retrieval_source"] = "hybrid"
            item["boosts"] = contributors[url][:6]
            merged.append(item)

        return {
            "query": query,
            "enriched_query": controlled_out["enriched_query"],
            "ontology_context": controlled_out["ontology_context"],
            "entities": controlled_out["entities"],
            "results": merged,
        }
