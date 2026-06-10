import settings


def get_llm(max_tokens=None):
    """
    Retorna una instancia del LLM.
    Si hi ha OPENAI_API_KEY configurada, usa OpenAI.
    Si no, usa Ollama (model local gratuit).
    """
    if settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("sk-your"):
        from langchain_openai import ChatOpenAI
        kwargs = {
            "model": settings.LLM_MODEL,
            "api_key": settings.OPENAI_API_KEY,
            "temperature": 0.3,
        }
        if max_tokens:
            kwargs["max_tokens"] = max_tokens
        print(f"[LLM] Usant OpenAI: {settings.LLM_MODEL}")
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
        print(f"[LLM] Usant Ollama local: {model}")
        return ChatOllama(**kwargs)
