import chromadb
from utils import SingletonMeta
import settings


class VectorStore(metaclass=SingletonMeta):
    """Emmagatzematge vectorial basat en ChromaDB (substitueix ElasticSearch per al PoC)."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
        self.collection = self.client.get_or_create_collection(
            name="fib_documents",
            metadata={"hnsw:space": "cosine"}
        )

    def add_documents(self, ids, documents, embeddings, metadatas=None):
        """Afegeix documents amb els seus embeddings a la col-leccio."""
        # ChromaDB requires list of lists for embeddings
        emb_list = [e if isinstance(e, list) else e.tolist() for e in embeddings]
        self.collection.add(
            ids=ids,
            documents=documents,
            embeddings=emb_list,
            metadatas=metadatas,
        )

    def search(self, query_embedding, n_results=5):
        """Cerca els n documents mes similars per embedding."""
        emb = query_embedding if isinstance(query_embedding, list) else query_embedding.tolist()
        return self.collection.query(
            query_embeddings=[emb],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )

    def count(self):
        """Retorna el nombre de documents indexats."""
        return self.collection.count()

    def reset(self):
        """Esborra tota la col-leccio i la recrea."""
        self.client.delete_collection("fib_documents")
        self.collection = self.client.get_or_create_collection(
            name="fib_documents",
            metadata={"hnsw:space": "cosine"}
        )
