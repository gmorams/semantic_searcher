import chromadb
from utils import SingletonMeta
import settings


class VectorStore(metaclass=SingletonMeta):
    """Almacen vectorial sobre ChromaDB."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name="fib_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, ids, documents, embeddings, metadatas=None):
        # ChromaDB necesita los embeddings como lista de listas
        emb_list = [e if isinstance(e, list) else e.tolist() for e in embeddings]
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=emb_list,
            metadatas=metadatas,
        )

    def upsert_documents(self, ids, documents, embeddings, metadatas=None):
        """Insert o update idempotente."""
        emb_list = [e if isinstance(e, list) else e.tolist() for e in embeddings]
        self.collection.upsert(
            ids=ids,
            documents=documents,
            embeddings=emb_list,
            metadatas=metadatas,
        )

    def search(self, query_embedding, n_results=5):
        emb = query_embedding if isinstance(query_embedding, list) else query_embedding.tolist()
        return self.collection.query(
            query_embeddings=[emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def count(self):
        return self.collection.count()

    def reset(self):
        """Borra y recrea la coleccion."""
        self.client.delete_collection("fib_documents")
        self.collection = self.client.get_or_create_collection(
            name="fib_documents",
            metadata={"hnsw:space": "cosine"}
        )
