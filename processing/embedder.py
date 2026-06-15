from sentence_transformers import SentenceTransformer
from utils import SingletonMeta
import settings


class Embedder(metaclass=SingletonMeta):
    """Genera embeddings vectorials per a text usant Sentence Transformers."""

    def __init__(self):
        model = settings.EMBEDDING_MODEL
        device = settings.EMBEDDING_DEVICE
        print(f"Carregant model d'embeddings: {model} ({device})...")
        try:
            self.model = SentenceTransformer(model, device=device)
        except Exception as e:
            print(f"Error amb {device}, usant CPU: {e}")
            self.model = SentenceTransformer(model, device="cpu")
        print(f"Model d'embeddings carregat: {model}")

    def embed(self, text: str):
        """Retorna el vector d'embedding per al text donat."""
        return self.model.encode(text)

    def embed_batch(self, texts: list):
        """Retorna embeddings per a una llista de textos."""
        return self.model.encode(texts)
