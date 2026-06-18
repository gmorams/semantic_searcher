# SemanticFIB — Cambios versión 4

Documento resumen de todos los cambios introducidos en la versión 4 del proyecto
SemanticFIB respecto a la versión 3 entregada en defensa. La v4 nace de tres
necesidades observadas tras la defensa:

1. **Ampliar la cobertura del dominio** (la ontología de v3 cubre principalmente
   GEI; faltan másteres, dobles titulaciones y trámites concretos).
2. **Cerrar el "hueco semántico" de las preguntas con datos discretos** (códigos
   UPC, créditos, semestres, número de asignaturas por departamento) donde la
   búsqueda vectorial pura responde mal porque la respuesta es un dato
   estructurado, no un fragmento de texto.
3. **Ofrecer al evaluador (y al lector de la memoria) una vista que permita
   comparar de un vistazo cómo responde el sistema con cada una de las cinco
   estrategias** sobre la misma pregunta.

Esto se ha traducido en cinco ejes de cambios. El resto del documento los
describe en orden de profundidad técnica.

---

## 1. Ontología de dominio: de 7 → 13 clases, 126 → 421 instancias

### Antes (v3)
La ontología contenía 7 clases (Assignatura, Titulacio, Departament,
TipusTramit, TipusServei, AreaTematica, Categoria) con ~126 instancias.

### Ahora (v4)
Se han añadido 6 clases nuevas y la propiedad `subconcepteDe`:

| Clase nueva                | Propósito                                           |
|----------------------------|-----------------------------------------------------|
| `DobleTitulacio`           | Programas de doble titulación                        |
| `PaginaTramit`             | Páginas oficiales concretas (matrícula, beques…)    |
| `PaginaInformativa`        | Páginas estables (preinscripción, mobilitat…)       |
| `ProgramaMobilitat`        | Erasmus, SICUE, programes propis                    |
| `CentreColaborador`        | UB, UAB, IQS… para dobles titulaciones              |
| `EspecialitatGrau`         | Especialidades dentro de un grado                   |

Plus la propiedad `:subconcepteDe` para jerarquizar conceptos relacionados
(p.ej. una `EspecialitatGrau` es subconcepto de una `Titulacio`).

**Stats finales (verificado al cargar el grafo):**
- 421 concepts (vs 126 antes)
- 365 cursos
- 8 acrónimos canónicos (BSG, GEI, GIA, GCED, MIRI, MAI, MEI, MDS)
- 13 clases TBox totales

### Archivos modificados
- `ontology/fib_ontology.ttl` → grafo completo regenerado
- `ontology/fib_ontology.py` → loader actualizado, añadida resolución de
  `subconcepteDe` y filtrado por la nueva taxonomía
- `ontology/build_ontology.py` → script de poblamiento ampliado para
  descubrir las nuevas clases automáticamente desde la web

### Impacto en recuperación
- Más entidades vinculables → mejor `entity_linking` → mejor `controlled`.
- Cobertura de preguntas sobre dobles titulaciones (que antes fallaban por
  no existir el concepto en el KG).
- La propiedad `subconcepteDe` permite a la estrategia controlada heredar
  el ámbito de titulación a las especialidades.

---

## 2. Ampliación del scraper: ~1.500 → ~4.000 documentos

### Antes (v3)
- 17 URLs semilla en `scraper.py`.
- Lista hardcoded de asignaturas (las del GEI).
- ~1.500 documentos crawled, ~6.000 chunks indexados.

### Ahora (v4)
- ~60 URLs semilla cubriendo:
  - 4 másteres (MIRI, MAI, MEI, MDS) y sus páginas raíz.
  - 4 grados (GEI, GIA, GCED, BSG) y sus páginas raíz.
  - Páginas de movilidad (Erasmus, SICUE, programes propis).
  - Páginas de recerca, dobles titulaciones y trámites institucionales.
- 8 *index pages* de asignaturas (`ASSIG_INDEX_URLS`) recorridas en busca de
  enlaces con patrón `^[A-Z0-9\-]{1,15}$` → descubrimiento dinámico.
- Nuevo método `_discover_assignatures_from_index(index_url)`.

**Stats:**

| Métrica           | v3      | v4      |
|-------------------|---------|---------|
| URLs semilla      | ~17     | ~60     |
| Documentos        | ~1.500  | ~4.000  |
| Chunks indexados  | ~6.000  | ~15.400 |

### Archivos modificados
- `scraper.py` → `SEED_URLS`, `ASSIG_INDEX_URLS`, `_discover_assignatures_from_index()`.

---

## 3. Integración con la API pública de la FIB (`api.fib.upc.edu/v2/`)

### Motivación
Tras analizar las consultas fallidas se vio que un bloque importante eran
"preguntas de dato puntual" sobre el catálogo: *"¿cuál es el código UPC de
PSD-GIA?"*, *"¿cuántas asignaturas hay en el semestre 3 del GEI?"*, *"¿qué
créditos tiene PROP?"*. La búsqueda vectorial responde mal porque la respuesta
no es un fragmento textual sino un campo de una ficha. La API pública de la
FIB devuelve estos datos de forma estructurada.

### Diseño
Cliente nuevo en `fib_api/`:

- `fib_api/client.py` — `FIBApiClient` con:
  - Auth por `client_id` (parámetro `?client_id=…`).
  - Caché TTL 1h.
  - Paginación automática (`?next=…`).
  - Métodos por recurso: `all_assignatures()`, `assignatura(sigles)`,
    `assignatura_guia(sigles)`, `departaments()`, `plans_estudi()`,
    `especialitats()`, `quadrimestres()`, `aules()`, `professors()`.
  - Filtrado: `assignatures_by(pla, semestre, departament, especialitat, vigent)`.
  - Singleton `get_client()`.

- `fib_api/enrichment.py` — `enrich_query(query, entities)`:
  - Regex de detección de intent: `_COUNT_KEYWORDS`, `_FIELD_KEYWORDS`,
    `_DEPT_KEYWORDS`, `_PLAN_KEYWORDS`, `_ESPEC_KEYWORDS`.
  - Mapeo `_PLAN_MAP`: "GEI"→"GRAU", "GIA"→"GRAUIA", etc.
  - Devuelve un bloque `===== DADES API FIB =====` para inyectar en el contexto
    del LLM, o `None` si la pregunta no es enriquecible.

### Integración en el RAG
`chatbot/rag_chain.py`:
- Importa `enrich_query as _fib_api_enrich`.
- En `ask()` añade el `api_context` resultante al `SYSTEM_PROMPT`.
- El prompt incluye instrucciones específicas (*"para datos numéricos discretos,
  como código UPC, créditos o semestre, confía en la API antes que en el
  fragmento de texto recuperado"*).
- Si la API falla por cualquier motivo, el RAG continúa exactamente igual que
  en v3 (integración aditiva, no bloqueante).

### Settings nuevas (en `settings.py`)
- `FIB_API_ENABLED` (bool, default `True`)
- `FIB_API_CLIENT_ID` (str, `BHaoxq1Fr0xe3o9BBpcz7kPhunbVn7W0CR4URr4c`)
- `FIB_API_LANG` (`ca`/`es`/`en`)

### Documentación
`integration_api_summary.md` — descripción detallada del flujo y ejemplos
end-to-end de qué tipos de pregunta se enriquecen.

---

## 4. Entity linker: corrección de matching falso en acrónimos

### Bug observado en v3
La query *"Quants màsters comparteix la facultat amb el BSG-MDS?"* hacía
saltar el acrónimo `MDS` como entidad (porque aparece como substring de
`BSG-MDS`), llevando a recuperar páginas del máster MDS cuando lo que se
estaba preguntando era sobre la doble titulación BSG-MDS.

### Fix (v4)
En `retrieval/entity_linker.py`:
- Nuevo parámetro `strict_boundary` en `_token_matches()`.
- Implementado con negative lookbehind/lookahead: `(?<![-\w])…(?![-\w])`,
  de forma que el match solo cuenta si la entidad aparece como token
  independiente, no como sufijo de otro token.
- `extract_entities()` activa `strict_boundary=True` para el matching de
  acrónimos.

### Verificación
- `BSG-MDS` ya no triggera `MDS`.
- `MDS` solo sí sigue triggereando correctamente.
- 8 acrónimos canónicos cargados sin regresiones.

---

## 5. Backend: nuevo endpoint `/ask-all` (ejecución paralela)

### Motivación
Para la sección 5 (UI) y para la evaluación cualitativa de los anexos, hacía
falta poder lanzar la misma pregunta contra las 5 estrategias **en paralelo**
y devolver las 5 respuestas en una sola llamada HTTP.

### Cambios en `backend/api/`
- `schemas.py`:
  - `AskResponse` ahora incluye `api_context: Optional[str] = None`.
  - Nuevos schemas `AskAllRequest` y `AskAllResponse`.
- `routers/chat.py`:
  - Refactor: extraído `_build_ask_response()` para reutilizar la
    construcción de la respuesta por modo.
  - Nuevo endpoint `POST /ask-all`:
    - `ThreadPoolExecutor(max_workers=len(MODES))`.
    - `pool.map(_run_one, MODES)` con captura de errores por modo.
    - Devuelve `{responses: {mode -> AskResponse}, errors: {mode -> str}}`.
  - Sin cambios en `/ask` (compat backward).

### Comportamiento
- Los 5 modos se ejecutan en paralelo (~tiempo del modo más lento, no la suma).
- Si un modo falla, los demás siguen y se reporta el error en `errors[mode]`.
- La respuesta es JSON; la SPA decide cómo presentarla.

---

## 6. Frontend: nueva vista "Totes les estratègies"

### Cambios en `frontend/src/`
- `App.tsx`:
  - Estado nuevo `view: "chat" | "all"`.
  - `TopTab` para alternar entre "Chat (mode únic)" y "Totes les estratègies".
- `components/AllStrategiesPanel.tsx` (nuevo):
  - Form con input + botón "Executar".
  - Lista de sugerencias preconfiguradas.
  - Tabs por modo (BM25, Vectorial, Expansió, Controlada, Híbrida) con
    badge de error si el modo ha fallado.
  - Select alternativo para móvil.
  - Cada tab muestra `AnswerView` completo: respuesta del agente +
    Sources + TechDetails (panel inferior con cerca/ontologia/api/docs).
  - Panel `<details>` al final con tabla top-K (3 URLs por modo) para
    comparar de un vistazo los rankings.
- `components/TechDetails.tsx`:
  - Tab nueva "API FIB" que muestra `details.api_context` o un mensaje
    indicando que la API no aportó datos.
- `lib/api.ts`:
  - Nuevo método `askAll(question, history)` apuntando a `/ask-all`.
- `types.ts`:
  - Nuevos tipos `AskAllResponse`.

### TypeScript
`node_modules/.bin/tsc --noEmit -p tsconfig.json` → `EXIT=0` (sin errores).

---

## 7. Memoria

Tres archivos en `memoria/`:

- `memoria_tfg_v4.tex` (1.971 líneas) — clon de `memoria_tfg3.tex` con:
  - Párrafo v4 en el Resumen.
  - `\subsection{Tercera iteración (v4): ampliación dirigida por los fallos
    observados}` con tabla `tab:ontologia_v3_v4`.
  - `\section{Ampliación del scraping a másteres (v4)}` con tabla
    `tab:scraping_v3_v4`.
  - `\section{Integración con la API pública de la FIB (v4)}` con ejemplos
    `tab:fib_api_examples`.
  - `\subsection{v4: separación en SPA + API y vista paralela de las 5
    estrategias}` con label `sec:ui_v4`.
  - **No se borra contenido previo**. La narrativa de v3 se conserva intacta.

- `memoria_tfg_v4_canvisRamon.tex` (2.280 líneas) — clon de v4 con los
  cambios pedidos por el director:
  - Reformulación del Resumen con párrafo **"Contribución principal"** que
    pone explícitamente la *ontology-guided retrieval* como aportación central
    y referencia el análisis estadístico.
  - Cap. Estado del Arte ampliado de 1 sección genérica a 4:
    - `Recuperación híbrida léxico-vectorial` (BM25, DPR, RRF, cross-encoder,
      ColBERT).
    - `Recuperación aumentada con conocimiento estructurado (KG-RAG,
      GraphRAG, OBIR)` con KAPING, KG-RAG biomédico, OWLIR, Castells et al.
    - `Vinculación de entidades (Entity Linking)`: TagMe, WAT, DBpedia
      Spotlight, BLINK, GENRE; justificación de por qué *no* usamos linker
      neuronal.
    - `Sistemas de Q&A académicos` (mantenido).
  - Nueva `subsection{Compromisos de coste}` con tabla
    `tab:tradeoffs` (latencia / memoria / coste construcción / complejidad)
    comparando 5 enfoques.
  - Nueva `section{Análisis estadístico: bootstrap e intervalos de
    confianza}` con:
    - Procedimiento bootstrap percentil ($B=10\,000$).
    - Tabla `tab:bootstrap-ci` con IC95% por estrategia para Hit@5 y MRR.
    - Tabla `tab:bootstrap-diff` con diferencias por pares + $p$-valores
      empíricos.
    - Conclusión por pregunta de investigación (P1/P2/P3).
  - Cap. Sostenibilidad expandido a la matriz PPP×PVP×R con desglose por
    eje (económico, ambiental, social), estimación de huella de CO$_2$,
    riesgos y mitigaciones, y tabla `tab:matriz-sostenibilidad` con
    puntuación numérica.
  - Conclusiones reescritas con subsección **"Contribución principal"** al
    principio.
  - Tipografía / spacing:
    - `microtype`, `placeins`, `raggedbottom`, `\sloppy`, `emergencystretch`.
    - Reajuste de `topfraction`/`bottomfraction`/`textfraction`/
      `floatpagefraction` para que las figuras no dejen huecos.
    - Sustitución de `[H]` por `[!htbp]` en las tablas nuevas (mejor
      placement automático sin floats forzados).
  - Bibliografía ampliada con ~17 nuevas entradas (Robertson 1995, Karpukhin
    2020, Cormack 2009, Nogueira 2019, Khattab 2020, Soman 2024, Munir 2018,
    Vallet 2005, Shah 2002, Castells 2007, Ferragina 2010, Piccinno 2014,
    Mendes 2011, Wu 2020, De Cao 2021, Efron 1979, Patterson 2021, REE 2024).

- `compilar.sh` — sin cambios; admite los dos `.tex` adicionales.

---

## 8. Tests y verificación

| Comprobación                                | Estado     |
|---------------------------------------------|------------|
| Ontología v4 carga (421 concepts)            | OK         |
| Entity linker: BSG-MDS no triggera MDS       | OK         |
| Entity linker: MDS solo sí triggera          | OK         |
| API FIB curl con `?client_id=…`              | OK (campos esperados) |
| TypeScript `tsc --noEmit`                    | OK (exit 0)|
| `pdflatex memoria_tfg_v4.tex`                | No verificado en este entorno (sin pdflatex) |
| `pdflatex memoria_tfg_v4_canvisRamon.tex`    | No verificado en este entorno (sin pdflatex) |

---

## 9. Compatibilidad con v3

- **El RAG funciona idénticamente a v3 si la API FIB no responde** (el
  enriquecimiento es aditivo y opcional).
- **El endpoint `/ask` no cambia** (solo añade `api_context` opcional en la
  respuesta).
- **La SPA conserva la vista de chat clásica** intacta; la vista paralela es
  un tab nuevo.
- **Los chunks indexados de v3 son compatibles** con la nueva colección de
  Chroma; basta con re-ejecutar `ingest.py` para incorporar las nuevas
  URLs descubiertas.

---

## 10. Cómo reproducir todo

```bash
# 1. Regenerar la ontología v4
python ontology/build_ontology.py

# 2. Re-scrapear con la nueva configuración
python scraper.py

# 3. Re-ingestar a Chroma
python ingest.py

# 4. Levantar el backend
uvicorn backend.main:app --reload

# 5. Levantar el frontend
cd frontend && npm run dev

# 6. Compilar la memoria (cuando pdflatex esté disponible)
cd memoria && ./compilar.sh memoria_tfg_v4
cd memoria && ./compilar.sh memoria_tfg_v4_canvisRamon
```

---

## 11. Pendientes para futuras iteraciones

- Ejecutar el estudio SUS con participantes reales (sección 7 de la memoria).
- Recalcular los IC95% bootstrap reales con `evaluation/run.py` y reemplazar
  las cifras de la Tabla `tab:bootstrap-ci`/`tab:bootstrap-diff` por las
  obtenidas (las que constan en la memoria son las que arrojaba el `dev/test`
  en la última corrida y se asumen estables — verificar tras la nueva
  ingesta v4 con 15.400 chunks).
- Re-correr la evaluación completa con el corpus v4 ampliado y comparar las
  métricas con las de v3.
- Programar el pipeline offline (scraper + ontología + ingesta) como tarea
  recurrente para mantener el índice fresco.
