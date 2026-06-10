"""
Pipeline RAG (Retrieval Augmented Generation) amb enriquiment ontologic.

Flux:
  1. L'usuari fa una pregunta
  2. L'ontologia enriqueix la consulta amb termes relacionats
  3. Es genera l'embedding de la consulta enriquida
  4. ChromaDB retorna els documents mes similars
  5. El LLM genera una resposta basada EXCLUSIVAMENT en els documents recuperats
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from chatbot.llm import get_llm
from db.vector_store import VectorStore
from processing.embedder import Embedder
from ontology.fib_ontology import enrich_query, get_ontology_context
import settings


SYSTEM_PROMPT = """Ets l'assistent de la Facultat d'Informatica de Barcelona (FIB) de la UPC.

INSTRUCCIONS:
1. Basa la teva resposta en la informacio dels DOCUMENTS RECUPERATS de sota. Extreu i sintetitza la informacio rellevant.
2. Si els documents contenen informacio relacionada amb la pregunta, utilitza-la per respondre. No cal que sigui una coincidencia exacta.
3. Si realment NO hi ha cap document rellevant, digues: "No he trobat informacio sobre aixo. Contacta amb la secretaria de la FIB (fib.secretaria.fib@upc.edu)."
4. Cita la font URL entre parentesis al final de cada punt rellevant.
5. Respon en el MATEIX idioma que l'usuari. Per defecte, catala.
6. Sigues clar, estructurat i util.

CONTEXT ONTOLOGIC:
{ontology_context}

===== DOCUMENTS RECUPERATS =====
{retrieved_docs}
===== FI =====
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{question}"),
])


class RAGChain:
    """Cadena RAG: consulta -> ontologia -> retrieval -> LLM -> resposta fonamentada."""

    def __init__(self):
        self.llm = get_llm()
        self.vector_store = VectorStore()
        self.embedder = Embedder()
        self.chain = prompt | self.llm

    def ask(self, question: str, chat_history: list = None) -> dict:
        if chat_history is None:
            chat_history = []

        # 1. Enriquiment ontologic
        enriched_query = enrich_query(question)

        # 2. Context ontologic per al prompt
        ontology_ctx = get_ontology_context(question)

        # 3. Cerca vectorial
        query_embedding = self.embedder.embed(enriched_query)
        results = self.vector_store.search(
            query_embedding=query_embedding,
            n_results=settings.TOP_K,
        )

        # 4. Formatar documents
        docs_text, retrieved_docs_detail = self._format_results(results)
        n_docs = len(results["documents"][0]) if results and results["documents"] else 0

        # 5. Generar resposta
        response = self.chain.invoke({
            "question": question,
            "ontology_context": ontology_ctx if ontology_ctx else "Cap context ontologic especific.",
            "retrieved_docs": docs_text if docs_text else "NO S'HAN TROBAT DOCUMENTS. Informa l'usuari que no tens informacio.",
            "chat_history": chat_history,
        })

        # 6. Fonts
        sources = []
        if results and results["metadatas"]:
            for meta in results["metadatas"][0]:
                src = meta.get("source", "")
                if src and src not in sources:
                    sources.append(src)

        return {
            "answer": response.content,
            "sources": sources,
            "enriched_query": enriched_query,
            "ontology_context": ontology_ctx,
            "num_docs_retrieved": n_docs,
            "retrieved_docs": retrieved_docs_detail,
        }

    def _format_results(self, results):
        """Retorna (text_per_prompt, llista_detall_per_ui)."""
        if not results or not results["documents"] or not results["documents"][0]:
            return "", []

        parts = []
        details = []
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            title = meta.get("title", "Document")
            source = meta.get("source", "")
            section = meta.get("section", "")
            similarity = max(0, 1 - dist)

            header = f"[Document {i+1}] Font: {source}"
            if section:
                header += f" | Seccio: {section}"
            parts.append(f"{header}\nTitol: {title}\nContingut:\n{doc}\n")

            details.append({
                "title": title,
                "source": source,
                "section": section,
                "similarity": round(similarity, 3),
                "preview": doc[:200] + "..." if len(doc) > 200 else doc,
            })

        return "\n".join(parts), details
