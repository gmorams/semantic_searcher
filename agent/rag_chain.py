"""Pipeline RAG con estrategia de busqueda configurable."""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from agent.llm import get_llm
from retrieval import get_retriever, MODES
import settings

try:
    from fib_api import enrich_query as _fib_api_enrich
except Exception:  # pragma: no cover
    _fib_api_enrich = None


SYSTEM_PROMPT = """Ets l'assistent de la Facultat d'Informatica de Barcelona (FIB) de la UPC.

INSTRUCCIONS:
1. Basa la teva resposta en la informacio dels DOCUMENTS RECUPERATS de sota. Extreu i sintetitza la informacio rellevant.
2. Si els documents contenen informacio relacionada amb la pregunta, utilitza-la per respondre. No cal que sigui una coincidencia exacta.
3. Si realment NO hi ha cap document rellevant, digues: "No he trobat informacio sobre aixo. Contacta amb la secretaria de la FIB (fib.secretaria.fib@upc.edu)."
4. Cita la font URL entre parentesis al final de cada punt rellevant.
5. Respon en el MATEIX idioma que l'usuari. Per defecte, catala.
6. Sigues clar, estructurat i util.

CONTEXT ONTOLOGIC (coneixement estructurat del domini):
{ontology_context}

{api_context}
===== DOCUMENTS RECUPERATS =====
{retrieved_docs}
===== FI =====

IMPORTANT sobre les DADES API FIB:
- Quan la pregunta es sobre camps puntuals d'una assignatura (codi UPC, credits,
  semestre, departament, llengues, prerequisits) o sobre conteig/llistat per
  filtres (assignatures d'un semestre/pla/departament), confia en aquestes
  dades estructurades per davant del text dels documents recuperats.
- No inventis valors numerics ni codis: si l'API no els retorna, digues que no
  els tens i remet a la pagina canonica corresponent.
"""

CONDENSE_PROMPT = """Reescriu l'ultima pregunta de l'usuari com una pregunta autonoma i completa en el mateix idioma, incorporant el context necessari de la conversa. Respon NOMES amb la pregunta reescrita, sense explicacions.

Conversa:
{history}

Ultima pregunta: {question}

Pregunta autonoma:"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])


class RAGChain:
    """Cadena RAG: consulta -> retriever -> LLM -> respuesta."""

    def __init__(self, mode=None):
        self.mode = mode or settings.RETRIEVAL_MODE
        if self.mode not in MODES:
            raise ValueError(f"Modo desconocido: {self.mode}")
        self.llm = get_llm()
        self.retriever = get_retriever(self.mode)
        self.chain = prompt | self.llm

    def _condense_question(self, question, chat_history):
        """Reformula una pregunta de seguimiento como pregunta autonoma."""
        if not chat_history:
            return question
        history_text = "\n".join(
            f"{'Usuari' if m.type == 'human' else 'Assistent'}: {m.content[:300]}"
            for m in chat_history[-6:]
        )
        try:
            response = self.llm.invoke(
                CONDENSE_PROMPT.format(history=history_text, question=question)
            )
            condensed = response.content.strip().strip('"')
            return condensed if condensed else question
        except Exception:
            return question

    def ask(self, question, chat_history=None):
        if chat_history is None:
            chat_history = []

        # condensar solo cuando hay historial
        search_question = self._condense_question(question, chat_history)

        retrieval = self.retriever.search(search_question, top_k=settings.TOP_K)
        results = retrieval["results"]

        # enriquecimiento opcional con la API publica de la FIB
        api_context = ""
        if getattr(settings, "FIB_API_ENABLED", False) and _fib_api_enrich is not None:
            try:
                api_context = _fib_api_enrich(
                    search_question,
                    entities=retrieval.get("entities", []),
                ) or ""
            except Exception:
                api_context = ""

        docs_text = self._format_docs_for_prompt(results)
        response = self.chain.invoke({
            "question": question,
            "ontology_context": retrieval["ontology_context"] or "Cap context ontologic especific.",
            "api_context": api_context,
            "retrieved_docs": docs_text or "NO S'HAN TROBAT DOCUMENTS. Informa l'usuari que no tens informacio.",
            "chat_history": chat_history,
        })

        # fuentes unicas en orden de ranking
        sources = []
        for item in results:
            src = item["source"]
            if src and src not in sources:
                sources.append(src)

        return {
            "answer": response.content,
            "sources": sources,
            "mode": self.mode,
            "search_question": search_question,
            "enriched_query": retrieval["enriched_query"],
            "ontology_context": retrieval["ontology_context"],
            "api_context": api_context or None,
            "entities": retrieval.get("entities", []),
            "num_docs_retrieved": len(results),
            "retrieved_docs": results,
        }

    def _format_docs_for_prompt(self, results):
        parts = []
        for i, item in enumerate(results, start=1):
            header = f"[Document {i}] Font: {item['source']}"
            if item["section"]:
                header += f" | Seccio: {item['section']}"
            parts.append(f"{header}\nTitol: {item['title']}\nContingut:\n{item['content']}\n")
        return "\n".join(parts)
