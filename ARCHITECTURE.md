# SemanticFIB — Arquitectura del sistema

Este documento explica la arquitectura de despliegue del proyecto y las decisiones
que la motivan. La capa de dominio (scraping, ingesta, ontología, recuperación,
RAG) se mantiene tal cual; lo que se añade es la capa de **servicio HTTP** y la
**interfaz web SPA**, junto con su empaquetado.

## 1. Punto de partida

La primera versión del proyecto era un único `app.py` de Streamlit que
mezclaba presentación y orquestación. Funciona en local, pero no es lo que se
espera de una pieza de software que aspira a ser:

- **reutilizable** (que otra app o la propia facultad la pueda consumir),
- **desplegable** (que un compañero o un técnico de la facultad pueda
  levantarla sin reaprender Streamlit),
- **extensible** (que añadir un endpoint nuevo o cambiar la UI no implique
  tocar la lógica de búsqueda).

## 2. Opciones que se consideraron

### A. FastAPI + React (Vite) + Docker Compose &nbsp;✅ implementada

- **Backend**: FastAPI expone una API REST (`/api/v1/ask`, `/search`,
  `/compare`, `/ontology/*`, `/stats`) con OpenAPI auto-documentada en `/docs`.
- **Frontend**: SPA en Vite + React + TypeScript + Tailwind, sirve la
  experiencia conversacional, el explorador de la ontología y el comparador
  de estrategias.
- **Empaquetado**: dos imágenes Docker (`api`, `web`) más un servicio
  opcional `ollama` para el LLM local; orquestado con Docker Compose.
- **Datos persistentes**: volúmenes para `chroma_db/`, `ontology/*.ttl` y
  `scraped_data/`. La ingesta se ejecuta como tarea puntual contra esos
  volúmenes.

#### Por qué encaja con este proyecto
- El alcance es pequeño en pantallas (chat + explorador + comparador) pero
  rico en backend; tiene sentido invertir la complejidad en el lado servidor.
- Exponer una API REST convierte el proyecto en un **componente reusable**:
  el día de mañana, un widget del Racó o una extensión de navegador pueden
  llamar a `POST /api/v1/ask` sin acoplarse a la UI de Streamlit.
- El despliegue es portátil: cualquier VPS (Hetzner, OVH, DigitalOcean) o
  cualquier plataforma con soporte Docker (Render, Railway, Fly.io) sirve.
- Mantiene la promesa del TFG de funcionar **100% local** sin dependencias
  cloud de pago.

### B. Cloud-native gestionado (FastAPI en Cloud Run/Fargate + Qdrant Cloud + OpenAI + IaC)

- Backend FastAPI desplegado en un servicio gestionado de contenedores
  (Cloud Run o AWS App Runner / ECS Fargate; **no** Lambda, porque el
  arranque en frío con un modelo de embeddings de varios cientos de MB es
  inaceptable). Instancia mínima = 1 para evitar cold-starts.
- Vector store gestionado: **Qdrant Cloud** o **Pinecone** en lugar de
  ChromaDB persistido en disco.
- LLM: **OpenAI** o **Amazon Bedrock**, porque Ollama no es trivial en
  serverless gestionado.
- Frontend: SPA en **Vercel** o **CloudFront + S3**.
- Infraestructura como código con **Terraform**, CI/CD con **GitHub Actions**
  (test → build → push → deploy).

#### Por qué no la elegimos (de momento)
- Hace perder una de las conclusiones del TFG: *"sistema 100 % local sin
  costes recurrentes"*.
- Tres servicios gestionados con coste mensual y secrets management.
- Es la siguiente iteración natural si el proyecto va a producción para los
  estudiantes; queda apuntada como **trabajo futuro**.

### Por qué se descartaron otras

- **Streamlit Cloud / Hugging Face Spaces**: simple, pero deja el proyecto
  igual de monolítico y poco reusable.
- **Lambda + API Gateway puro**: el coste de arranque del modelo de
  embeddings (~400 MB) lo hace prohibitivo para este caso de uso.
- **Django + DRF**: aporta ORM, admin, etc., que aquí no usaríamos; FastAPI
  es más ligero y su autodocumentación OpenAPI es exactamente lo que
  queremos para un componente que aspira a ser consumido por otros.

## 3. Diagrama lógico de la arquitectura implementada

```
                ┌──────────────────────────────┐
                │   Browser (React SPA)        │
                │   - Chat                     │
                │   - Ontology explorer        │
                │   - Strategy comparator      │
                └──────────────┬───────────────┘
                               │  fetch / SSE
                               ▼
                ┌──────────────────────────────┐
                │   FastAPI (uvicorn)          │
                │   /api/v1/ask                │
                │   /api/v1/search             │
                │   /api/v1/compare            │
                │   /api/v1/ontology/*         │
                │   /api/v1/stats              │
                │   /docs (OpenAPI)            │
                └──────────────┬───────────────┘
                               │  (in-process)
                ┌──────────────┴───────────────┐
                │   Dominio (sin cambios)      │
                │   chatbot/ retrieval/        │
                │   ontology/ db/ processing/  │
                └──────────────┬───────────────┘
                               │
                ┌──────────┐   │   ┌──────────────────┐
                │ChromaDB  │◀──┼───┤ Ollama / OpenAI  │
                │(volume)  │   │   │ (LLM)            │
                └──────────┘   │   └──────────────────┘
                               │
                       ┌───────┴───────┐
                       │ fib_ontology  │
                       │   .ttl (vol.) │
                       └───────────────┘
```

## 4. Capas del nuevo código

```
semantic_searcher/
├── backend/             # NUEVO — servicio HTTP
│   ├── api/
│   │   ├── main.py      # FastAPI app + CORS + lifespan
│   │   ├── deps.py      # Singletons (vector store, ontología, RAG chain)
│   │   ├── schemas.py   # Pydantic models — contrato HTTP
│   │   └── routers/     # endpoints temáticos
│   ├── tests/           # tests de humo
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # NUEVO — SPA Vite + React + TS + Tailwind
│   ├── src/
│   ├── Dockerfile       # build multistage + nginx
│   └── nginx.conf
├── docker-compose.yml   # NUEVO — orquestación local y de despliegue
├── chatbot/ retrieval/ ontology/ db/ processing/   # SIN CAMBIOS
└── app.py               # SIN CAMBIOS — sigue funcionando como demo
```

## 5. Cómo correrlo

### En local (sin Docker)

```bash
# Terminal 1: backend
cd backend
pip install -r requirements.txt
uvicorn api.main:app --reload --port 8000

# Terminal 2: frontend
cd frontend
npm install
npm run dev      # → http://localhost:5173

# Streamlit (legacy) sigue funcionando si lo quieres usar:
python3 -m streamlit run app.py
```

### Con Docker Compose (despliegue reproducible)

```bash
docker compose up --build
# → web:  http://localhost:8080
# → api:  http://localhost:8000/docs
```

Si quieres el LLM local dentro de Docker:

```bash
docker compose --profile ollama up --build
# y dentro del servicio ollama: ollama pull llama3.2
```

## 6. Por qué esto justifica complejidad de software

Un revisor académico o un ingeniero que reciba el proyecto verá:

- **Contrato HTTP** versionado (`/api/v1`) con esquemas Pydantic — punto de
  extensión claro para clientes futuros.
- **Separación neta** entre presentación (SPA), API (controladores
  delgados), dominio (lógica de búsqueda) y datos (Chroma + RDF).
- **Empaquetado reproducible** (Docker + Compose) que reduce el
  *time-to-first-query* de un desarrollador nuevo a un comando.
- **Tests** de la API que verifican el contrato sin depender del LLM.
- **Documentación generada** automáticamente (Swagger UI en `/docs`,
  ReDoc en `/redoc`).

Todo esto sin reescribir la lógica de búsqueda, que es donde está el
contenido investigador del TFG.
