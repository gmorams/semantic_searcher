"""
Script d'indexacio: carrega documents (scraping web + PDFs) i els emmagatzema a ChromaDB.

Us:
    python3 ingest.py --from-scrape         # Indexa les dades scrapejades de la FIB
    python3 ingest.py --from-scrape --reset  # Esborra BD i reindexa
    python3 ingest.py fitxer.pdf             # Indexa un PDF concret
"""

import sys
import os
import json
import hashlib

sys.path.insert(0, os.path.dirname(__file__))

from processing.pdf_loader import load_and_chunk_pdf
from processing.embedder import Embedder
from db.vector_store import VectorStore
import settings

SCRAPED_DATA_FILE = os.path.join(os.path.dirname(__file__), "scraped_data", "fib_documents.json")

# Patrons que indiquen contingut de menu/navegacio (no informacio real)
NAV_INDICATORS = [
    "Vols estudiar un grau?",
    "Accés als estudis",
    "Portes Obertes",
]


def _is_nav_content(text):
    """Detecta si un text es principalment un menu de navegacio."""
    matches = sum(1 for pattern in NAV_INDICATORS if pattern in text)
    if matches >= 2:
        # Si te molts indicadors de nav, nomes acceptar si te prou text propi
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        short_lines = sum(1 for l in lines if len(l) < 40)
        if short_lines > len(lines) * 0.6:
            return True
    return False


def make_id(text, url=""):
    """Genera un ID unic i deterministic per a un chunk."""
    content = f"{url}:{text[:200]}"
    return hashlib.md5(content.encode()).hexdigest()


def chunk_text(text, chunk_size=800, chunk_overlap=200):
    """Divideix text llarg en chunks amb overlap."""
    if len(text) <= chunk_size:
        return [text]
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - chunk_overlap
    return chunks


def ingest_scraped_data(reset=False):
    """Indexa les dades scrapejades de fib.upc.edu a ChromaDB."""
    if not os.path.exists(SCRAPED_DATA_FILE):
        print(f"ERROR: No es troben dades scrapejades a {SCRAPED_DATA_FILE}")
        print("Executa primer: python3 scraper.py")
        sys.exit(1)

    with open(SCRAPED_DATA_FILE, "r", encoding="utf-8") as f:
        documents = json.load(f)

    print(f"{'='*60}")
    print(f"  INDEXACIO DE DADES SCRAPEJADES - FIB")
    print(f"{'='*60}")
    print(f"  Font:       {SCRAPED_DATA_FILE}")
    print(f"  Documents:  {len(documents)}")
    print(f"  Chunk size: {settings.CHUNK_SIZE}")
    print(f"  ChromaDB:   {settings.CHROMA_PERSIST_DIR}")
    print(f"{'='*60}\n")

    store = VectorStore()

    if reset:
        print("Esborrant base de dades anterior...")
        store.reset()

    # 1. Generar chunks de tots els documents
    print("1. Generant chunks dels documents scrapejats...")
    all_chunks = []
    for doc in documents:
        content = doc.get("content", "").strip()
        if not content or len(content) < 30:
            continue

        # Filtrar documents que son menus de navegacio
        if _is_nav_content(content):
            continue

        title = doc.get("title", "")
        url = doc.get("url", "")
        section = doc.get("section", "")

        text_chunks = chunk_text(content, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)

        for i, chunk in enumerate(text_chunks):
            all_chunks.append({
                "id": make_id(chunk, url),
                "text": chunk,
                "title": title,
                "url": url,
                "section": section,
            })

    print(f"   -> {len(all_chunks)} chunks generats de {len(documents)} documents\n")

    if not all_chunks:
        print("ERROR: No s'han generat chunks")
        sys.exit(1)

    # 2. Generar embeddings i indexar
    print("2. Generant embeddings i indexant a ChromaDB...")
    embedder = Embedder()

    batch_size = 32
    total = len(all_chunks)

    for i in range(0, total, batch_size):
        batch = all_chunks[i:i + batch_size]

        ids = [c["id"] for c in batch]
        texts = [c["text"] for c in batch]
        metadatas = [{
            "title": c["title"],
            "source": c["url"],
            "section": c["section"],
        } for c in batch]

        embeddings = embedder.embed_batch(texts)
        embeddings_list = [emb.tolist() for emb in embeddings]

        try:
            store.add_documents(
                ids=ids,
                documents=texts,
                embeddings=embeddings_list,
                metadatas=metadatas,
            )
        except Exception as e:
            # Pot passar amb IDs duplicats, saltar
            print(f"   [WARN] Batch {i}: {e}")

        done = min(i + batch_size, total)
        if done % 100 < batch_size:
            print(f"   -> Indexats {done}/{total} chunks")

    print(f"\n{'='*60}")
    print(f"  INDEXACIO COMPLETADA!")
    print(f"  Total documents a ChromaDB: {store.count()}")
    print(f"{'='*60}")
    print(f"\n  Ara pots executar el chatbot amb:")
    print(f"  python3 -m streamlit run app.py")


def ingest_pdf(pdf_path, reset=False):
    """Indexa un fitxer PDF a ChromaDB."""
    if not os.path.exists(pdf_path):
        print(f"ERROR: No es troba el fitxer {pdf_path}")
        sys.exit(1)

    print(f"Indexant PDF: {pdf_path}")
    store = VectorStore()
    if reset:
        store.reset()

    chunks = load_and_chunk_pdf(pdf_path, settings.CHUNK_SIZE, settings.CHUNK_OVERLAP)
    print(f"  -> {len(chunks)} chunks generats")

    embedder = Embedder()
    batch_size = 32
    total = len(chunks)

    for i in range(0, total, batch_size):
        batch = chunks[i:i + batch_size]
        ids = [c["id"] for c in batch]
        texts = [c["text"] for c in batch]
        metadatas = [{"title": c["title"], "source": c["source"], "section": c.get("section", "")} for c in batch]
        embeddings = embedder.embed_batch(texts)
        store.add_documents(ids=ids, documents=texts, embeddings=[e.tolist() for e in embeddings], metadatas=metadatas)
        print(f"  -> Indexats {min(i+batch_size, total)}/{total}")

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
        print("  python3 ingest.py --from-scrape         # Indexa dades scrapejades")
        print("  python3 ingest.py --from-scrape --reset  # Reset + indexa")
        print("  python3 ingest.py fitxer.pdf              # Indexa un PDF")
