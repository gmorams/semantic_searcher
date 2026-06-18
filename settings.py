import os
from dotenv import load_dotenv

load_dotenv()

# LLM (OpenAI u Ollama)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "paraphrase-multilingual-MiniLM-L12-v2")
EMBEDDING_DEVICE = os.getenv("EMBEDDING_DEVICE", "cpu")

# ChromaDB
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", os.path.join(os.path.dirname(__file__), "chroma_db"))

# Chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
MIN_CHUNK_LENGTH = int(os.getenv("MIN_CHUNK_LENGTH", "120"))

# Recuperacion
TOP_K = int(os.getenv("TOP_K", "5"))
CANDIDATE_K = int(os.getenv("CANDIDATE_K", "40"))
RETRIEVAL_MODE = os.getenv("RETRIEVAL_MODE", "hybrid")

# Fusion RRF (busqueda hibrida)
RRF_K = int(os.getenv("RRF_K", "60"))
RRF_WEIGHT_CONTROLLED = float(os.getenv("RRF_WEIGHT_CONTROLLED", "1.0"))
RRF_WEIGHT_BM25 = float(os.getenv("RRF_WEIGHT_BM25", "0.6"))
RRF_WEIGHT_DENSE = float(os.getenv("RRF_WEIGHT_DENSE", "0.6"))

# Integracion con la API publica de la FIB
FIB_API_ENABLED = os.getenv("FIB_API_ENABLED", "true").lower() in ("1", "true", "yes")
FIB_API_CLIENT_ID = os.getenv("FIB_API_CLIENT_ID", "BHaoxq1Fr0xe3o9BBpcz7kPhunbVn7W0CR4URr4c")
FIB_API_LANG = os.getenv("FIB_API_LANG", "ca")
