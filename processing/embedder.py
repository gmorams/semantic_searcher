from sentence_transformers import SentenceTransformer
from utils import SingletonMeta
import settings


class Embedder(metaclass=SingletonMeta):
    """Genera embeddings vectoriales mediante Sentence Transformers."""

    def __init__(self):
        model = settings.EMBEDDING_MODEL
        device = settings.EMBEDDING_DEVICE
        try:
            self.model = SentenceTransformer(model, device=device)
        except Exception:
            # fallback a CPU si el dispositivo configurado falla
            self.model = SentenceTransformer(model, device="cpu")

    def embed(self, text: str):
        return self.model.encode(text)

    def embed_batch(self, texts: list):
        return self.model.encode(texts)
