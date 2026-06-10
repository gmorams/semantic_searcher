"""
SemanticFIB - Buscador Semantic Intel-ligent de la FIB
Interficie professional Streamlit.

Execucio:
    python3 -m streamlit run app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage
from db.vector_store import VectorStore
from ontology.fib_ontology import FIB_ONTOLOGY, RELATIONS

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(
    page_title="SemanticFIB",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# CSS
# ============================================================================

st.markdown("""
<style>
    /* Header */
    .main-header {
        background: linear-gradient(135deg, #003366 0%, #0066cc 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #cce0ff; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* Source cards */
    .source-card {
        background: #f8f9fa;
        border-left: 4px solid #0066cc;
        padding: 0.6rem 1rem;
        margin: 0.4rem 0;
        border-radius: 0 6px 6px 0;
        font-size: 0.85rem;
    }
    .source-card a { color: #0066cc; text-decoration: none; }
    .source-card a:hover { text-decoration: underline; }

    /* Similarity badge */
    .sim-badge {
        display: inline-block;
        background: #e8f5e9;
        color: #2e7d32;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #f5f7fa; }

    /* Ontology tag */
    .ont-tag {
        display: inline-block;
        background: #e3f2fd;
        color: #1565c0;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8rem;
        margin: 2px;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.image("https://www.fib.upc.edu/sites/fib/files/LogoFib2.png", width=180)
    st.markdown("### SemanticFIB")
    st.caption("Buscador semantic amb ontologies + LLM")
    st.divider()

    # Estat BD
    store = VectorStore()
    doc_count = store.count()

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Fragments", doc_count)
    with col2:
        st.metric("Conceptes", len(FIB_ONTOLOGY))

    st.divider()

    # Ontologia interactiva
    st.markdown("#### Ontologia del domini")
    selected_concept = st.selectbox(
        "Explora conceptes:",
        list(FIB_ONTOLOGY.keys()),
        index=None,
        placeholder="Selecciona un concepte...",
    )

    if selected_concept:
        data = FIB_ONTOLOGY[selected_concept]
        syns = data.get("sinonims", [])
        rels = data.get("relacionats", [])
        subs = [s for s in data.get("subtipus", []) if s]

        if syns:
            st.markdown("**Sinonims:**")
            st.markdown(" ".join(f'<span class="ont-tag">{s}</span>' for s in syns[:6]), unsafe_allow_html=True)
        if rels:
            st.markdown("**Relacionats:**")
            st.markdown(" ".join(f'<span class="ont-tag">{r}</span>' for r in rels[:8]), unsafe_allow_html=True)
        if subs:
            st.markdown("**Subtipus:**")
            st.markdown(" ".join(f'<span class="ont-tag">{s}</span>' for s in subs), unsafe_allow_html=True)

        graph_rels = [(s, r, o) for s, r, o in RELATIONS if s == selected_concept or o == selected_concept]
        if graph_rels:
            st.markdown("**Relacions:**")
            for s, r, o in graph_rels:
                st.markdown(f"  `{s}` --*{r}*--> `{o}`")

    st.divider()

    # Arquitectura
    with st.expander("Arquitectura del sistema"):
        st.markdown("""
        ```
        Pregunta
          |
          v
        [Ontologia] -> Enriquiment
          |
          v
        [Embedder] -> Vector query
          |
          v
        [ChromaDB] -> Top-K docs
          |
          v
        [LLM] -> Resposta fonamentada
        ```

        **Components:**
        - Embeddings: `multilingual-MiniLM`
        - Vector Store: ChromaDB
        - LLM: Ollama (llama3.2)
        - Dades: Scraping fib.upc.edu
        """)

    st.divider()
    st.caption("TFG - Giancarlo Morales Munoz")
    st.caption("UPC - FIB | Dir: Ramon Sanguesa")

# ============================================================================
# MAIN
# ============================================================================

# Header
st.markdown("""
<div class="main-header">
    <h1>🔍 SemanticFIB</h1>
    <p>Buscador semantic de la Facultat d'Informatica de Barcelona | Basat en ontologies + LLM</p>
</div>
""", unsafe_allow_html=True)

# Check BD
if doc_count == 0:
    st.error("No hi ha documents indexats. Executa primer:")
    st.code("python3 scraper.py && python3 ingest.py --from-scrape --reset", language="bash")
    st.stop()

# Init session
if "messages" not in st.session_state:
    st.session_state.messages = []
if "rag_chain" not in st.session_state:
    from chatbot.rag_chain import RAGChain
    with st.spinner("Carregant models..."):
        st.session_state.rag_chain = RAGChain()

# Suggeriments inicials
if not st.session_state.messages:
    st.markdown("#### Prova alguna d'aquestes preguntes:")
    suggestions = [
        "Com funciona la matricula al grau d'informatica?",
        "Quines especialitats te el GEI?",
        "Quins tramits puc fer a secretaria?",
        "Que es el treball de fi de grau?",
        "Quines beques hi ha disponibles?",
    ]
    cols = st.columns(len(suggestions))
    for i, (col, sug) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sug})
                st.rerun()

# Chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍🎓" if msg["role"] == "user" else "🔍"):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and "details" in msg:
            det = msg["details"]

            # Fonts
            if det.get("sources"):
                with st.expander(f"📚 Fonts ({len(det['sources'])} URLs)"):
                    for src in det["sources"]:
                        st.markdown(f'<div class="source-card"><a href="{src}" target="_blank">{src}</a></div>', unsafe_allow_html=True)

            # Debug
            with st.expander("🔬 Detalls tecnics"):
                tab1, tab2, tab3 = st.tabs(["Cerca", "Ontologia", "Documents"])

                with tab1:
                    st.markdown(f"**Query original:** {det.get('question', '')}")
                    st.markdown(f"**Query enriquida:** `{det.get('enriched_query', '')}`")
                    st.markdown(f"**Documents recuperats:** {det.get('num_docs_retrieved', 0)}")

                with tab2:
                    ont = det.get("ontology_context", "")
                    if ont:
                        st.code(ont)
                    else:
                        st.info("Cap concepte ontologic detectat a la consulta")

                with tab3:
                    for doc_detail in det.get("retrieved_docs", []):
                        sim = doc_detail.get("similarity", 0)
                        badge_color = "#e8f5e9" if sim > 0.5 else "#fff3e0" if sim > 0.3 else "#ffebee"
                        st.markdown(f"""**{doc_detail['title']}** <span class="sim-badge">{sim:.1%}</span>
                        \n{doc_detail.get('preview', '')}
                        \n*Font: {doc_detail.get('source', '')}*""", unsafe_allow_html=True)
                        st.divider()

# Input
if question := st.chat_input("Fes una pregunta sobre la FIB..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🔍"):
        with st.spinner("Cercant a la base de dades de la FIB..."):
            chat_history = []
            for msg in st.session_state.messages[:-1]:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

            result = st.session_state.rag_chain.ask(question, chat_history)

        st.markdown(result["answer"])

        details = {
            "question": question,
            "enriched_query": result["enriched_query"],
            "ontology_context": result["ontology_context"] or "",
            "num_docs_retrieved": result["num_docs_retrieved"],
            "sources": result["sources"],
            "retrieved_docs": result.get("retrieved_docs", []),
        }

        # Fonts inline
        if result["sources"]:
            with st.expander(f"📚 Fonts ({len(result['sources'])} URLs)"):
                for src in result["sources"]:
                    st.markdown(f'<div class="source-card"><a href="{src}" target="_blank">{src}</a></div>', unsafe_allow_html=True)

        # Debug
        with st.expander("🔬 Detalls tecnics"):
            tab1, tab2, tab3 = st.tabs(["Cerca", "Ontologia", "Documents"])
            with tab1:
                st.markdown(f"**Query original:** {question}")
                st.markdown(f"**Query enriquida:** `{result['enriched_query']}`")
                st.markdown(f"**Documents recuperats:** {result['num_docs_retrieved']}")
            with tab2:
                if result["ontology_context"]:
                    st.code(result["ontology_context"])
                else:
                    st.info("Cap concepte ontologic detectat")
            with tab3:
                for doc_detail in result.get("retrieved_docs", []):
                    sim = doc_detail.get("similarity", 0)
                    st.markdown(f"""**{doc_detail['title']}** <span class="sim-badge">{sim:.1%}</span>
                    \n{doc_detail.get('preview', '')}
                    \n*Font: {doc_detail.get('source', '')}*""", unsafe_allow_html=True)
                    st.divider()

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "details": details,
        })
