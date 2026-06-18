"""
Indexacion: carga documentos (scraping web + PDFs) y los almacena en ChromaDB.
"""

import sys
import os
import json
import hashlib

sys.path.insert(0, os.path.dirname(__file__))

from langchain_text_splitters import RecursiveCharacterTextSplitter

from processing.pdf_loader import load_and_chunk_pdf
from processing.embedder import Embedder
from db.vector_store import VectorStore
import settings

SCRAPED_DATA_FILE = os.path.join(os.path.dirname(__file__), "scraped_data", "fib_documents.json")

# patrones que delatan contenido de menu/navegacion, no informacion util
NAV_INDICATORS = [
    "Vols estudiar un grau?",
    "Accés als estudis",
    "Portes Obertes",
]


def _is_nav_content(text):
    """True si el texto parece un menu de navegacion."""
    matches = sum(1 for pattern in NAV_INDICATORS if pattern in text)
    if matches >= 2:
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        short_lines = sum(1 for l in lines if len(l) < 40)
        if short_lines > len(lines) * 0.6:
            return True
    return False


def _canonical_urls():
    """URLs canonicas de la ontologia: se conservan aunque tengan poco texto."""
    try:
        from ontology.fib_ontology import get_ontology
        return {c["url"].rstrip("/") for c in get_ontology().concepts.values() if c["url"]}
    except Exception:
        return set()


def make_id(url, chunk_index, text):
    """ID determinista por (url, posicion, hash del texto)."""
    digest = hashlib.md5(text.encode()).hexdigest()[:12]
    url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
    return f"{url_hash}-{chunk_index}-{digest}"


def get_splitter():
    return RecursiveCharacterTextSplitter(
        chunk_size=settings.CHUNK_SIZE,
        chunk_overlap=settings.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", "? ", "! ", "; ", ", ", " ", ""],
    )


def deduplicate_documents(documents, canonical=None):
    """Fusiona documentos con contenido identico.

    La FIB sirve la misma pagina bajo varias URLs (una por titulacion);
    si una de ellas esta en la ontologia, la usamos como representante.
    """
    canonical = canonical or set()
    seen = {}
    deduped = []
    for doc in documents:
        content = (doc.get("content") or "").strip()
        if not content:
            continue
        digest = hashlib.md5(content.encode()).hexdigest()
        url = (doc.get("url") or "").rstrip("/")
        if digest in seen:
            kept = seen[digest]
            kept_url = (kept.get("url") or "").rstrip("/")
            if url in canonical and kept_url not in canonical:
                # la nueva URL es canonica: pasa a ser la representante
                kept["duplicate_urls"].append(kept.get("url", ""))
                kept["url"] = doc.get("url", "")
                kept["title"] = doc.get("title", kept.get("title", ""))
            else:
                kept["duplicate_urls"].append(doc.get("url", ""))
            continue
        entry = dict(doc)
        entry["duplicate_urls"] = []
        seen[digest] = entry
        deduped.append(entry)
    return deduped


def ingest_scraped_data(reset=False):
    """Indexa en ChromaDB las paginas previamente scrapeadas de fib.upc.edu."""
    if not os.path.exists(SCRAPED_DATA_FILE):
        print(f"ERROR: No es troben dades scrapejades a {SCRAPED_DATA_FILE}")
        print("Executa primer: python3 scraper.py")
        sys.exit(1)

    with open(SCRAPED_DATA_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    canonical = _canonical_urls()

    store = VectorStore()
    if reset:
        store.reset()

    # 1. deduplicacion (priorizando URLs canonicas de la ontologia)
    deduped = deduplicate_documents(documents, canonical=canonical)

    # 2. chunking
    splitter = get_splitter()
    all_chunks = []
    skipped_short = 0

    for doc in deduped:
        content = doc.get("content", "").strip()
        url = (doc.get("url") or "").rstrip("/")
        is_canonical = url in canonical

        if _is_nav_content(content) and not is_canonical:
            continue

        min_len = 30 if is_canonical else settings.MIN_CHUNK_LENGTH
        if len(content) < min_len:
            skipped_short += 1
            continue

        title = doc.get("title", "")
        section = doc.get("section", "")

        for i, chunk in enumerate(splitter.split_text(content)):
            chunk = chunk.strip()
            if len(chunk) < min_len:
                continue
            # descartamos chunks sin apenas contenido alfabetico
            alpha = sum(1 for ch in chunk if ch.isalpha())
            if alpha < len(chunk) * 0.5:
                continue
            all_chunks.append({
                "id": make_id(url, i, chunk),
                "text": chunk,
                "title": title,
                "url": doc.get("url", ""),
                "section": section,
            })

    # deduplicacion final de chunks (secciones repetidas dentro de la misma pagina)
    unique_chunks = {}
    for c in all_chunks:
        if c["id"] not in unique_chunks:
            unique_chunks[c["id"]] = c
    all_chunks = list(unique_chunks.values())

    if not all_chunks:
        print("ERROR: No s'han generat chunks")
        sys.exit(1)

    # 3. embeddings + upsert en ChromaDB
    embedder = Embedder()
    batch_size = 32
    total = len(all_chunks)

    for i in range(0, total, batch_size):
        batch = all_chunks[i:i + batch_size]
        ids = [c["id"] for c in batch]
        texts = [c["text"] for c in batch]
        # incluimos titulo y seccion en el texto que se embebe (contexto del chunk)
        embed_texts = [
            " | ".join(p for p in [c["title"], c["section"]] if p) + "\n" + c["text"]
            if (c["title"] or c["section"]) else c["text"]
            for c in batch
        ]
        metadatas = [{
            "title": c["title"],
            "source": c["url"],
            "section": c["section"],
        } for c in batch]

        embeddings = embedder.embed_batch(embed_texts)
        store.upsert_documents(
            ids=ids,
            documents=texts,
            embeddings=[e.tolist() for e in embeddings],
            metadatas=metadatas,
        )

    print(f"\n{'='*60}")
    print(f"  INDEXACIO COMPLETADA!")
    print(f"  Total chunks a ChromaDB: {store.count()}")
    print(f"{'='*60}")
    print(f"\n  Ara pots executar el cercador amb:")
    print(f"  python3 -m streamlit run app.py")


def ingest_pdf(pdf_path, reset=False):
    """Indexa un PDF concreto en ChromaDB."""
    if not os.path.exists(pdf_path):
        print(f"ERROR: No es troba el fitxer {pdf_path}")
        sys.exit(1)

    store = VectorStore()
    if reset:
        store.reset()

    chunks = load_and_chunk_pdf(pdf_path, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

    embedder = Embedder()
    batch_size = 32
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        ids = [c["id"] for c in batch]
        texts = [c["text"] for c in batch]
        metadatas = [{"title": c["title"], "source": c["source"], "section": c.get("section", "")} for c in batch]
        embeddings = embedder.embed_batch(texts)
        store.upsert_documents(ids=ids, documents=texts, embeddings=[e.tolist() for e in embeddings], metadatas=metadatas)

    print(f"\nTotal a ChromaDB: {store.count()}")


if __name__ == "__main__":
    reset = "--reset" in sys.argv
    from_scrape = "--from-scrape" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]

    if from_scrape:
        ingest_scraped_data(reset=reset)
    elif args:
        ingest_pdf(args[0], reset=reset)
    else:
        print("Us:")
        print("  python3 ingest.py --from-scrape          # Indexa dades scrapejades")
        print("  python3 ingest.py --from-scrape --reset  # Reset + indexa")
        print("  python3 ingest.py fitxer.pdf             # Indexa un PDF")
