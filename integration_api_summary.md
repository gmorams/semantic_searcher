# Integració de l'API pública de la FIB (v4)

Aquest document explica com s'ha integrat l'API pública `api.fib.upc.edu/v2/`
dins el pipeline de SemanticFIB, perquè el sistema combini els resultats del
buscador semàntic (RAG sobre la web de la FIB) amb dades estructurades en JSON
de la pròpia FIB.

## 1. Decisió de disseny

L'API exposa **dades estructurades i sempre actualitzades** que la web només
ofereix com a text llarg (i sovint repetit per a cada titulació). Hi ha
preguntes que la indexació vectorial **mai respondrà bé** perquè requereixen:

- Un **camp puntual** (codi UPC, semestre, crèdits, departament, idioma…)
  d'una assignatura concreta.
- Un **conteig** o un **filtre** sobre el catàleg ("quantes assignatures té el
  semestre 3 del GEI", "quins departaments té la FIB", "llistat d'assignatures
  del dept. AC").
- La **guia docent** d'una assignatura (objectius, temari, metodologia…).

Per a aquest tipus de pregunta, una crida directa a l'API és **instantània,
exacta i barata**; el sistema vectorial seria més car, més lent i podria
retornar dades obsoletes o errònies (per exemple, un crèdit antic indexat
abans del canvi de pla).

Per tant, la integració s'ha pensat com una **capa additiva de context** que
s'injecta al prompt del LLM al costat del context ontològic i dels documents
recuperats. **No reemplaça** cap mòdul del retrieval; el complementa.

## 2. Mòdul nou: `fib_api/`

```
fib_api/
├── __init__.py
├── client.py         # Client HTTP cacheat
└── enrichment.py     # Detecció d'intents + construcció del bloc de context
```

### `client.py` — `FIBApiClient`

Client minimal i autocontingut:

- Autenticació amb només el **Client ID** (header `client_id`), passat com a
  configuració (`FIB_API_CLIENT_ID`, per defecte el de l'aplicació pública del
  TFG).
- Cache en memòria amb TTL d'1 h (les dades del catàleg canvien poc).
- Paginat automàtic (`?page=2…`) per als recursos de tipus llista.
- Mètodes d'alt nivell per als recursos més usats: `all_assignatures`,
  `assignatura(sigles)`, `assignatura_guia(sigles)`, `departaments`,
  `plans_estudi`, `quadrimestres`, `especialitats`, `aules`, `professors`.
- Helper d'agregació `assignatures_by(pla, semestre, departament,
  especialitat)` per resoldre preguntes de tipus "quantes/quines …".
- Singleton `get_client()` per evitar arrancar un client per crida.

Si l'API està caiguda o llença timeout, el client retorna `None`/`[]` i el
RAG segueix funcionant com abans (la integració mai és bloquejant).

### `enrichment.py` — `enrich_query(query, entities)`

Aquest és el cervell de la integració. La idea es separar la decisió en dues
etapes deterministes (sense LLM extra) i deixar al LLM final la
interpretació/resum:

1. **Resolució per codi**: les entitats detectades pel `entity_linker` ja
   inclouen la URL canònica de cada concepte. Quan una URL és del tipus
   `…/pla-destudis/assignatures/<CODI>`, en traiem el codi (PRO1, BSG-MDS,
   AD…) i fem `client.assignatura(codi)`. Si la pregunta tracta un camp
   concret (codi UPC, crèdits, semestre, llengua, prerequisits, guia docent),
   filtrem el bloc per mostrar només els camps rellevants.

2. **Agregació/filtre**: si la consulta conté paraules clau de count o de
   llistat ("quantes", "quants", "quines", "list", "llistat"…) i alguna
   marca de filtre detectable amb regex (semestre `S1..S8`, pla `GEI/GCED/
   GIA/GBIO/MEI/MIRI/MDS/MAI`, departament `AC/CS/EIO/…`), executem
   `assignatures_by(...)` sobre el catàleg cacheat i incloem en el context el
   número total i una mostra de fins a 25 sigles + nom.

3. **Taules petites**: si la consulta toca la llista de departaments / plans /
   especialitats, s'injecten directament des de l'API (són recursos petits i
   estables).

El resultat és un bloc de text encapçalat per `===== DADES API FIB
(estructurades) =====` que es concatena al prompt. Si no hi ha res a
afegir, retorna `None`.

#### Per què regex i no un altre LLM?

Una segona crida LLM "router" abans del retrieval afegeix 0,5–1,5 s per
consulta i un cost extra significatiu en producció. Per al subconjunt de
preguntes que ataca l'API (codis puntuals, comptes, llistes), el patró és
prou regular per resoldre amb regex sobre el text en català/castellà/anglès.
Si el regex no dispara res, el RAG funciona exactament igual que abans i és
el LLM final el que decideix què citar.

## 3. Modificacions a la cadena RAG

`chatbot/rag_chain.py`:

- Nova importació: `from fib_api import enrich_query as _fib_api_enrich`.
- Nou placeholder al `SYSTEM_PROMPT`: `{api_context}` (immediatament abans
  del bloc de documents recuperats).
- Nou pas al mètode `RAGChain.ask`: després del retrieval i abans de la
  generació, si `settings.FIB_API_ENABLED`, cridem `_fib_api_enrich(...)` amb
  la pregunta condensada i les entitats. El bloc resultant es passa com a
  variable de plantilla.
- Instruccions afegides al prompt perquè el LLM **prioritzi** les dades de
  l'API per a fets puntuals (codi UPC, crèdits, semestre…) i **no inventi**
  valors.
- El `result` retornat ara inclou `api_context` (per debug i visualització a
  la UI).

## 4. Endpoint, esquema i configuració

- `backend/api/schemas.py` — `AskResponse.api_context: Optional[str]`.
- `backend/api/routers/chat.py` — propagat des del resultat del RAG.
- `settings.py` — `FIB_API_ENABLED`, `FIB_API_CLIENT_ID`, `FIB_API_LANG`
  configurables per variable d'entorn.

## 5. Idioma

S'envia `Accept-Language: ca` per defecte (configurable). Els camps
multilingües de l'API (nom de l'assignatura, descripció dels departaments,
nom de les especialitats…) tornen en català, que casa amb el idioma majoritari
del corpus indexat i amb el to del xatbot.

## 6. Exemples de millora

| Pregunta | Comportament v3 | Comportament v4 |
|---|---|---|
| "quin és el codi UPC de PSD-GCED?" | Resposta vaga, possiblement "no ho sé". | API retorna `codi_upc=270218` exacte. |
| "quantes assignatures té S3 del GEI?" | Recompte aproximat a partir de fragments. | Filtre `pla=GRAU, semestre=S3` → número exacte i llista. |
| "quins departaments hi ha a la FIB?" | Resposta basada en paràgrafs incomplets. | Llista oficial dels 8 departaments amb cap i URL. |
| "en quin semestre és PRO1?" | Resposta correcta des dels documents. | Resposta correcta amb camp `semestre` (sense ambigüitat). |
| "guia docent de XC" | Només fragments de la web. | Camps específics de la guia (objectius, temari…). |

## 7. Tolerància a errors

- Timeout 10 s; tres reintents implícits (cache d'1 h amortitza les
  consultes repetides).
- Excepcions encapsulades: `RAGChain.ask` mai falla per problemes de l'API.
- El bloc d'API només s'injecta si la detecció determinista (regex + entity
  linker) troba alguna cosa rellevant: per a la majoria de preguntes
  obertes ("com em puc matricular?", "quan és el TFG?", "què és la FIB?")
  no s'afegeix res i el comportament és idèntic al v3.

## 8. Coexistència amb el retrieval ontològic

L'enriquiment via API és **complementari** al re-ranqueo guiat per
ontologia: l'ontologia tria les **pàgines** rellevants, l'API afegeix els
**fets numèrics o de catàleg** que les pàgines no contenen explícitament en
forma estructurada. En les preguntes on les dues fonts es solapen, el
prompt instrueix el LLM a confiar en els camps de l'API per als valors
discrets (codi UPC, crèdits, semestre, departament) i en els documents per
a la part narrativa (motivació, contingut conceptual, normativa).
