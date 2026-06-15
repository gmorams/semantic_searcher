"""
Pipeline RAG (Retrieval Augmented Generation) amb estrategia de cerca configurable.

Flux:
  1. Si hi ha historial, el LLM condensa la pregunta de seguiment en una
     pregunta autonoma (query condensation) perque el retrieval funcioni.
  2. El retriever del mode actiu (bm25 / dense / ontology / controlled /
     hybrid) recupera els documents mes rellevants.
  3. El LLM genera una resposta fonamentada EXCLUSIVAMENT en aquests documents,
     amb el context ontologic com a coneixement estructurat addicional.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from chatbot.llm import get_llm
from retrieval import get_retriever, MODES
import settings


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

===== DOCUMENTS RECUPERATS =====
{retrieved_docs}
===== FI =====
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
    """Cadena RAG: consulta -> retriever (mode configurable) -> LLM -> resposta."""

    def __init__(self, mode=None):
        self.mode = mode or settings.RETRIEVAL_MODE
        if self.mode not in MODES:
            raise ValueError(f"Mode desconegut: {self.mode}")
        self.llm = get_llm()
        self.retriever = get_retriever(self.mode)
        self.chain = prompt | self.llm

    def _condense_question(self, question, chat_history):
        """Reescriu preguntes de seguiment com a preguntes autonomes."""
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

        # 1. Condensacio de la pregunta (nomes si hi ha historial)
        search_question = self._condense_question(question, chat_history)

        # 2. Retrieval amb l'estrategia activa
        retrieval = self.retriever.search(search_question, top_k=settings.TOP_K)
        results = retrieval["results"]

        # 3. Generacio de la resposta
        docs_text = self._format_docs_for_prompt(results)
        response = self.chain.invoke({
            "question": question,
            "ontology_context": retrieval["ontology_context"] or "Cap context ontologic especific.",
            "retrieved_docs": docs_text or "NO S'HAN TROBAT DOCUMENTS. Informa l'usuari que no tens informacio.",
            "chat_history": chat_history,
        })

        # 4. Fonts uniques en ordre de ranking
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
