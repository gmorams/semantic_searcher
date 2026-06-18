import settings


def get_llm(max_tokens=None):
    """Devuelve la instancia LLM activa: OpenAI si hay clave, Ollama si no."""
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": settings.LLM_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.3,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        return ChatOpenAI(**kwargs)
    else:
        from langchain_ollama import ChatOllama
        model = settings.OLLAMA_MODEL
        kwargs = {
            "model": model,
            "temperature": 0.3,
        }
        if max_tokens:
            kwargs["num_predict"] = max_tokens
        return ChatOllama(**kwargs)
