from sentence_transformers import SentenceTransformer
from utils import measure_time, SingletonMeta
import settings

class Embedder(metaclass=SingletonMeta):
    def __init__(self):
        """
        Initializes the embedder by loading the specified Sentence Transformer model.
        """
        model = "BAAI/bge-m3"

        device = settings.EMBEDDING_DEVICE # cuda cpu

        try:
            self.model = SentenceTransformer(model, device=device) #si no va, fem cpu
        except Exception as e:
            print(e)
            print("Generating embeddings with cpu")

            self.model = SentenceTransformer(model, device="cpu")

    @measure_time
    def embed(self, text: str):
        """
        Returns the embedding for the provided text.

        Parameters:
            text (str): The input text to embed.

        Returns:
            numpy.ndarray: The embedding vector.
        """
        return self.model.encode(text)
    
    def embed2(self, text: str): # es igual que embed, pero no te el decorator (la podem cridar molts cops seguits desde el indexador sense que fagi tants prints)
        """
        Returns the embedding for the provided text.

        Parameters:
            text (str): The input text to embed.

        Returns:
            numpy.ndarray: The embedding vector.
        """
        return self.model.encode(text)
    
#"BAAI/bge-m3"
#"sentence-transformers/distiluse-base-multilingual-cased-v2"  short window size,   embedding size  512