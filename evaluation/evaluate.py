"""
Avaluacio automatica i reproduible de les estrategies de recuperacio.

Per a cada mode de cerca executa totes les consultes del golden set
(`evaluation/queries.json`) i calcula metriques estandard de recuperacio
d'informacio a nivell de pagina (URL):

    Hit@1 / Hit@3 / Hit@5   hi ha alguna URL rellevant al top-k?
    MRR                     mean reciprocal rank de la primera URL rellevant
    P@5                     precisio: fraccio del top-5 que es rellevant
    R@5                     recall: fraccio de les URLs rellevants trobades
    nDCG@5                  discounted cumulative gain normalitzat (binari)

Els resultats es desglossen per split (dev/test) per detectar sobreajust:
el split 'test' conte parafrasis held-out no usades durant el disseny.

Us:
    python3 evaluation/evaluate.py                      # tots els modes
    python3 evaluation/evaluate.py --modes bm25,hybrid  # modes concrets
    python3 evaluation/evaluate.py --split test         # nomes held-out
"""

import argparse
import csv
import json
import math
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from retrieval import get_retriever, MODES
from retrieval.base import normalize_url

EVAL_DIR = os.path.dirname(os.path.abspath(__file__))
QUERIES_FILE = os.path.join(EVAL_DIR, "queries.json")
RESULTS_DIR = os.path.join(EVAL_DIR, "results")

K = 5


def load_queries(split="all"):
    with open(QUERIES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    queries = data["queries"]
    if split != "all":
        queries = [q for q in queries if q["split"] == split]
    return queries


def retrieved_urls(retriever, query, k=K):
    """Top-k URLs uniques (en ordre de ranking) per a una consulta."""
    output = retriever.search(query, top_k=k * 4)
    urls = []
    for item in output["results"]:
        url = normalize_url(item["source"])
        if url and url not in urls:
            urls.append(url)
        if len(urls) >= k:
            break
    return urls


def evaluate_query(urls, relevant):
    relevant = {normalize_url(u) for u in relevant}
    hits = [1 if u in relevant else 0 for u in urls]

    first_rank = next((i + 1 for i, h in enumerate(hits) if h), None)
    rr = 1.0 / first_rank if first_rank else 0.0

    dcg = sum(h / math.log2(i + 2) for i, h in enumerate(hits))
    ideal_hits = min(len(relevant), len(urls)) or 1
    idcg = sum(1 / math.log2(i + 2) for i in range(ideal_hits))
    ndcg = dcg / idcg if idcg > 0 else 0.0

    n_found = len({u for u in urls if u in relevant})
    return {
        "hit@1": 1.0 if first_rank == 1 else 0.0,
        "hit@3": 1.0 if first_rank and first_rank <= 3 else 0.0,
        "hit@5": 1.0 if first_rank and first_rank <= 5 else 0.0,
        "mrr": rr,
        "p@5": sum(hits) / max(len(urls), 1),
        "r@5": n_found / len(relevant) if relevant else 0.0,
        "ndcg@5": ndcg,
        "first_rank": first_rank,
    }


def aggregate(per_query):
    if not per_query:
        return {}
    keys = ["hit@1", "hit@3", "hit@5", "mrr", "p@5", "r@5", "ndcg@5"]
    return {k: sum(q[k] for q in per_query) / len(per_query) for k in keys}


def evaluate_mode(mode, queries):
    print(f"\n>>> Avaluant mode: {mode} ({MODES[mode]})")
    retriever = get_retriever(mode)
    details = []
    for q in queries:
        urls = retrieved_urls(retriever, q["query"])
        metrics = evaluate_query(urls, q["relevant_urls"])
        details.append({
            "id": q["id"], "query": q["query"], "split": q["split"],
            "category": q["category"], "retrieved": urls,
            "relevant": q["relevant_urls"], **metrics,
        })
        mark = "+" if metrics["hit@5"] else "-"
        print(f"  [{mark}] ({q['split']}) {q['query'][:55]:<55} rank={metrics['first_rank']}")
    return details


def format_pct(value):
    return f"{value * 100:.1f}%"


def print_table(rows, title):
    print(f"\n{'='*86}")
    print(f"  {title}")
    print(f"{'='*86}")
    header = f"{'Mode':<12}{'Hit@1':>9}{'Hit@3':>9}{'Hit@5':>9}{'MRR':>8}{'P@5':>8}{'R@5':>8}{'nDCG@5':>9}"
    print(header)
    print("-" * 86)
    for mode, agg in rows:
        print(f"{mode:<12}{format_pct(agg['hit@1']):>9}{format_pct(agg['hit@3']):>9}"
              f"{format_pct(agg['hit@5']):>9}{agg['mrr']:>8.3f}{agg['p@5']:>8.3f}"
              f"{agg['r@5']:>8.3f}{agg['ndcg@5']:>9.3f}")


def save_results(all_details, timestamp):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    # Detall per consulta (JSON, per a analisi d'errors)
    detail_file = os.path.join(RESULTS_DIR, f"details_{timestamp}.json")
    with open(detail_file, "w", encoding="utf-8") as f:
        json.dump(all_details, f, ensure_ascii=False, indent=2)

    # Resum agregat (CSV, per a les taules de la memoria)
    csv_file = os.path.join(RESULTS_DIR, f"summary_{timestamp}.csv")
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["mode", "split", "n_queries", "hit@1", "hit@3", "hit@5",
                         "mrr", "p@5", "r@5", "ndcg@5"])
        for mode, details in all_details.items():
            for split in ["all", "dev", "test"]:
                subset = details if split == "all" else [d for d in details if d["split"] == split]
                if not subset:
                    continue
                agg = aggregate(subset)
                writer.writerow([mode, split, len(subset)] +
                                [round(agg[k], 4) for k in
                                 ["hit@1", "hit@3", "hit@5", "mrr", "p@5", "r@5", "ndcg@5"]])

    print(f"\nResultats guardats a:")
    print(f"  {csv_file}")
    print(f"  {detail_file}")


def main():
    parser = argparse.ArgumentParser(description="Avaluacio de les estrategies de cerca")
    parser.add_argument("--modes", default=",".join(MODES),
                        help=f"Modes separats per comes (disponibles: {','.join(MODES)})")
    parser.add_argument("--split", default="all", choices=["all", "dev", "test"])
    args = parser.parse_args()

    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    for m in modes:
        if m not in MODES:
            print(f"ERROR: mode desconegut '{m}'. Disponibles: {list(MODES)}")
            sys.exit(1)

    queries = load_queries(args.split)
    print(f"Golden set: {len(queries)} consultes (split={args.split})")

    all_details = {}
    for mode in modes:
        all_details[mode] = evaluate_mode(mode, queries)

    # Taules: global + per split
    for split, title in [("all", "RESULTATS GLOBALS"),
                         ("dev", "SPLIT DEV (consultes de disseny)"),
                         ("test", "SPLIT TEST (held-out: parafrasis no vistes)")]:
        rows = []
        for mode in modes:
            subset = (all_details[mode] if split == "all"
                      else [d for d in all_details[mode] if d["split"] == split])
            if subset:
                rows.append((mode, aggregate(subset)))
        if rows:
            print_table(rows, title)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_results(all_details, timestamp)


if __name__ == "__main__":
    main()
