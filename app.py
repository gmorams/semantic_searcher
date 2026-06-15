"""
SemanticFIB - Buscador Semantic Intel-ligent de la FIB
Interficie Streamlit amb seleccio d'estrategia de cerca i explorador d'ontologia.

Execucio:
    python3 -m streamlit run app.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import streamlit as st
from langchain_core.messages import HumanMessage, AIMessage

from db.vector_store import VectorStore
from ontology.fib_ontology import get_ontology
from retrieval import MODES

# ============================================================================
# CONFIG
# ============================================================================

st.set_page_config(
    page_title="SemanticFIB",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)

MODE_LABELS = {
    "hybrid": "Híbrida (RRF) — recomanada",
    "controlled": "Ontologia controlada + entity linking",
    "ontology": "Expansió ontològica naive",
    "dense": "Vectorial pura (baseline)",
    "bm25": "Lèxica BM25 (baseline)",
}

# CSS 

# Modifica tu bloque de estilos para que use variables de Streamlit
st.markdown("""
<style>
    /* El contenedor principal del encabezado conserva su gradiente corporativo */
    .main-header {
        background: linear-gradient(135deg, #003366 0%, #0066cc 100%);
        padding: 1.5rem 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    
    /* Forzar que el título de la cabecera SIEMPRE sea blanco (ya que el fondo es azul oscuro) */
    .main-header h1, .main-header p {
        color: #ffffff !important;
    }

    /* EL TRUCO CLAVE: Quita cualquier regla que obligue a la barra lateral a ser blanca 
       o negra, y deja que herede las variables oficiales de Streamlit */
    [data-testid="stSidebar"] {
        /* Usamos las variables nativas del tema activo */
        background-color: var(--background-color); 
        color: var(--text-color);
    }

    /* Asegurar que las tarjetas de métricas o textos secundarios se adapten */
    .metric-card {
        background-color: var(--secondary-background-color);
        border: 1px solid rgba(128, 128, 128, 0.2);
        padding: 1rem;
        border-radius: 8px;
        color: var(--text-color);
    }
</style>
""", unsafe_allow_html=True)

# CACHED RESOURCES

@st.cache_resource(show_spinner="Carregant base de dades...")
def load_store():
    return VectorStore()


@st.cache_resource(show_spinner="Carregant ontologia...")
def load_ontology():
    return get_ontology()


@st.cache_resource(show_spinner="Carregant models de cerca...")
def load_rag_chain(mode):
    from chatbot.rag_chain import RAGChain
    return RAGChain(mode=mode)


store = load_store()
ontology = load_ontology()
doc_count = store.count()
ont_stats = ontology.stats()

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ruta_logo = os.path.join(BASE_DIR, "logo_fib.png")
    st.image(ruta_logo, width=180)

    st.markdown("### SemanticFIB")
    st.caption("Buscador semàntic amb ontologia formal + LLM")
    st.divider()

    # Estrategia de cerca
    st.markdown("#### Estratègia de cerca")
    mode = st.radio(
        "Mode de recuperació:",
        list(MODE_LABELS.keys()),
        format_func=lambda m: MODE_LABELS[m],
        label_visibility="collapsed",
    )
    st.caption(MODES[mode])

    st.divider()

    # Metriques
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Fragments", doc_count)
    with col2:
        st.metric("Triples RDF", ont_stats["triples"])
    with col3:
        st.metric("Instàncies", ont_stats["instances"])

    st.divider()

    # Explorador de l'ontologia
    st.markdown("#### Ontologia del domini")
    grouped = ontology.concepts_by_type()
    sel_type = st.selectbox("Classe:", list(grouped.keys()))
    sel_label = st.selectbox(
        "Instància:",
        [c["label"] for c in grouped.get(sel_type, [])],
        index=None,
        placeholder="Selecciona...",
    )

    if sel_label:
        details = ontology.concept_details(sel_label)
        if details:
            if details.get("code"):
                st.markdown(f"**Codi:** `{details['code']}`")
            if details.get("synonyms"):
                st.markdown("**Etiquetes alternatives (SKOS):**")
                st.markdown(" ".join(
                    f'<span class="ont-tag">{s}</span>' for s in details["synonyms"][:8]
                ), unsafe_allow_html=True)
            if details.get("related"):
                st.markdown("**skos:related:**")
                st.markdown(" ".join(
                    f'<span class="ont-tag">{r}</span>' for r in details["related"]
                ), unsafe_allow_html=True)
            if details.get("url"):
                st.markdown(f"**Recurs canònic:** [{details['url'].split('/ca/')[-1]}]({details['url']})")
            if details.get("weight") and details["type"] == "Concepte acadèmic":
                st.markdown(f"**Pes d'intenció:** `{details['weight']}`")

    st.divider()

    with st.expander("Arquitectura del sistema"):
        st.markdown("""
        ```
        Pregunta
          |-- [Condensació LLM] (seguiment)
          |-- [Ontologia RDF] -> conceptes,
          |        expansió, entitats
          v
        [Retriever del mode actiu]
          bm25 | dense | ontology |
          controlled | hybrid (RRF)
          |
          v
        [ChromaDB] -> candidats -> rerank
          |
          v
        [LLM] -> Resposta fonamentada
        ```

        **Components:**
        - Ontologia: RDF/OWL (rdflib + SPARQL)
        - Embeddings: `multilingual-MiniLM`
        - Vector store: ChromaDB | Lèxic: BM25
        - LLM: Ollama / OpenAI
        - Dades: scraping fib.upc.edu
        """)

    st.divider()
    st.caption("TFG - Giancarlo Morales Munoz")
    st.caption("UPC - FIB | Dir: Ramon Sanguesa")

# ============================================================================
# MAIN
# ============================================================================

st.markdown(f"""
<div class="main-header">
    <h1>🔍 SemanticFIB</h1>
    <p>Buscador semàntic de la Facultat d'Informàtica de Barcelona |
    Ontologia formal + RAG | Mode actiu: <b>{MODE_LABELS[mode]}</b></p>
</div>
""", unsafe_allow_html=True)

if doc_count == 0:
    st.error("No hi ha documents indexats. Executa primer:")
    st.code("python3 scraper.py && python3 ingest.py --from-scrape --reset", language="bash")
    st.stop()

if "messages" not in st.session_state:
    st.session_state.messages = []

rag_chain = load_rag_chain(mode)


def render_details(det):
    """Panell de detalls tecnics d'una resposta."""
    tab1, tab2, tab3 = st.tabs(["Cerca", "Ontologia", "Documents"])

    with tab1:
        st.markdown(f"**Mode:** `{det.get('mode', '')}`")
        st.markdown(f"**Query original:** {det.get('question', '')}")
        if det.get("search_question") and det["search_question"] != det.get("question"):
            st.markdown(f"**Query condensada:** {det['search_question']}")
        st.markdown(f"**Query enriquida:** `{det.get('enriched_query', '')}`")
        if det.get("entities"):
            st.markdown("**Entitats enllaçades:**")
            for label, url in det["entities"]:
                st.markdown(f"- `{label}` → [{url.split('/ca/')[-1]}]({url})")
        st.markdown(f"**Documents recuperats:** {det.get('num_docs_retrieved', 0)}")

    with tab2:
        ont = det.get("ontology_context", "")
        if ont:
            st.code(ont)
        else:
            st.info("Cap concepte ontològic detectat a la consulta")

    with tab3:
        for d in det.get("retrieved_docs", []):
            score = d.get("score", d.get("similarity", 0))
            boosts = "".join(f'<span class="boost-badge">{b}</span>' for b in d.get("boosts", []))
            st.markdown(
                f"""**{d['title']}** <span class="sim-badge">score {score:.3f}</span> {boosts}
                \n{d.get('preview', '')}
                \n*Font: {d.get('source', '')}*""",
                unsafe_allow_html=True,
            )
            st.divider()


def render_sources(sources):
    if sources:
        with st.expander(f"📚 Fonts ({len(sources)} URLs)"):
            for src in sources:
                st.markdown(
                    f'<div class="source-card"><a href="{src}" target="_blank">{src}</a></div>',
                    unsafe_allow_html=True,
                )


# Suggeriments inicials
if not st.session_state.messages:
    st.markdown("#### Prova alguna d'aquestes preguntes:")
    suggestions = [
        "Com funciona la matrícula al grau d'informàtica?",
        "Quines especialitats té el GEI?",
        "Què s'estudia a XC?",
        "Quan són els exàmens finals?",
        "Vull anar d'Erasmus",
    ]
    cols = st.columns(len(suggestions))
    for i, (col, sug) in enumerate(zip(cols, suggestions)):
        with col:
            if st.button(sug, key=f"sug_{i}", use_container_width=True):
                st.session_state.messages.append({"role": "user", "content": sug})
                st.rerun()

# Historial
for msg in st.session_state.messages:
    with st.chat_message(msg["role"], avatar="🧑‍🎓" if msg["role"] == "user" else "🔍"):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "details" in msg:
            render_sources(msg["details"].get("sources", []))
            with st.expander("🔬 Detalls tècnics"):
                render_details(msg["details"])

# Input
if question := st.chat_input("Fes una pregunta sobre la FIB..."):
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user", avatar="🧑‍🎓"):
        st.markdown(question)

    with st.chat_message("assistant", avatar="🔍"):
        with st.spinner(f"Cercant ({MODE_LABELS[mode]})..."):
            chat_history = []
            for msg in st.session_state.messages[:-1]:
                if msg["role"] == "user":
                    chat_history.append(HumanMessage(content=msg["content"]))
                elif msg["role"] == "assistant":
                    chat_history.append(AIMessage(content=msg["content"]))

            result = rag_chain.ask(question, chat_history)

        st.markdown(result["answer"])

        details = {
            "question": question,
            "mode": result["mode"],
            "search_question": result.get("search_question", question),
            "enriched_query": result["enriched_query"],
            "ontology_context": result["ontology_context"] or "",
            "entities": result.get("entities", []),
            "num_docs_retrieved": result["num_docs_retrieved"],
            "sources": result["sources"],
            "retrieved_docs": result.get("retrieved_docs", []),
        }

        render_sources(result["sources"])
        with st.expander("🔬 Detalls tècnics"):
            render_details(details)

        st.session_state.messages.append({
            "role": "assistant",
            "content": result["answer"],
            "details": details,
        })

# ============================================================================
# COMPARISON MODE (for the defense: all the strategies at once)
# ============================================================================

st.divider()
with st.expander("⚖️ Comparador d'estratègies (executa la mateixa consulta amb tots els modes)"):
    comp_query = st.text_input("Consulta a comparar:", key="comp_query",
                               placeholder="p.ex. Quan són els exàmens finals?")
    if st.button("Comparar modes", disabled=not comp_query):
        from retrieval import get_retriever
        from retrieval.base import normalize_url

        comparison = {}
        progress = st.progress(0.0)
        for i, m in enumerate(MODE_LABELS):
            retriever = get_retriever(m)
            output = retriever.search(comp_query, top_k=10)
            urls = []
            for item in output["results"]:
                u = normalize_url(item["source"])
                if u and u not in urls:
                    urls.append(u)
                if len(urls) >= 3:
                    break
            comparison[m] = urls
            progress.progress((i + 1) / len(MODE_LABELS))
        progress.empty()

        rows = []
        for m, urls in comparison.items():
            rows.append({
                "Mode": MODE_LABELS[m],
                "Top 1": urls[0].split("/ca/")[-1] if len(urls) > 0 else "—",
                "Top 2": urls[1].split("/ca/")[-1] if len(urls) > 1 else "—",
                "Top 3": urls[2].split("/ca/")[-1] if len(urls) > 2 else "—",
            })
        st.dataframe(rows, use_container_width=True)
