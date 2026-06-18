# Ampliación de la ontología — SemanticFIB v3

Resumen de los cambios hechos para mejorar la recuperación, manteniendo intacto
todo lo que ya funcionaba (el modo `controlled` sigue en **92,5 % Hit@5 / MRR 0,82**
sobre el golden set, sin regresión).

## 1. Problema detectado

La consulta «*Si faig el màster de ciència de dades, amb quins centres puc fer
doble titulació?*» no encontraba la página correcta
(`/ca/mobilitat/dobles-titulacions`).

**Causa raíz:** `doble titulació` era solo un *sinónimo* del concepto genérico
`mobilitat`, cuyo `recursCanonic` apunta a `/ca/mobilitat`. La ontología sabía
que la consulta iba de movilidad, pero no conocía la **página de aterrizaje
específica**, así que ninguna estrategia con boost ontológico podía priorizarla.

El patrón se repetía con muchas otras subpáginas (departamentos, biblioteca,
gobierno, trámites concretos…): existían en la web pero no como instancias de la
ontología, así que el re-ranqueo controlado no las "veía".

## 2. Qué se ha añadido

### TBox — nuevas clases (de 7 a 13)
Modelan con más precisión el dominio real de la web:

- `Tramit` (subclase de `ConcepteAcademic`)
- `ProgramaMobilitat` (subclase de `ConcepteAcademic`)
- `UnitatRecerca` (subclase de `EntitatAcademica`)
- `EspaiFisic` (subclase de `EntitatAcademica`)
- `ServeiFIB` (subclase de `EntitatAcademica`)
- `OrganGovern` (subclase de `EntitatAcademica`)

### TBox — nueva propiedad de objeto
- `subconcepteDe`: jerarquía entre conceptos (p.ej. `dobles titulacions`
  → `subconcepteDe` → `mobilitat`). Se expone al LLM como contexto
  ("Forma part de: Mobilitat") para respuestas más coherentes.

Las propiedades de datos (`recursCanonic`, `pesIntencio`, `patroUrl`, `codi`)
**no se han modificado**: su semántica ya era la adecuada. Solo se ha ampliado
el rango de `pesIntencio` hasta 0,35 para las páginas de aterrizaje más
específicas (ver abajo).

### ABox — ~24 conceptos nuevos (instancias con URL canónica real)
Cada uno con etiquetas multilingües (SKOS), peso de intención, slug de URL,
clase y, si aplica, concepto padre:

- **Movilidad:** `dobles titulacions`, `programes de mobilitat`,
  `universitats partner`.
- **Recerca:** `recerca`, `departaments`, `grups de recerca`,
  `centres de recerca`, `inLab FIB`.
- **Espacios físicos:** `biblioteca`, `laboratoris`, `aules docents`.
- **Institucional:** `associacions`, `govern`, `la facultat en xifres`,
  `actes acadèmics`.
- **Trámites concretos:** `cita prèvia`, `bústia FIB`,
  `reconeixement de crèdits`, `canvi de menció`, `trasllat d'expedient`,
  `simultaneïtat d'estudis`, `certificats acadèmics`,
  `sol·licitud del títol`, `renúncia de matrícula`.

### Ajuste de cobertura
- Se quitó `doble titulació` de los sinónimos de `mobilitat` (ahora es su
  propio concepto con la URL correcta).
- Se añadió `ciència de dades` / `data science` como sinónimo del Màster MDS,
  para que se detecte aunque no se use la sigla.

### Pesos (`pesIntencio`)
Las páginas más específicas reciben un peso mayor que su concepto padre para
que ganen el re-ranqueo cuando ambos se detectan
(p.ej. `dobles titulacions` 0,35 > `mobilitat` 0,20).

## 3. Cambios de código

- **`ontology/build_ontology.py`**: nuevas clases, propiedad `subconcepteDe`,
  ~24 conceptos nuevos y soporte de los campos `class` / `parent` por concepto.
- **`ontology/fib_ontology.py`**: detección de los nuevos tipos de clase (los
  tipos `Assignatura`/`Grau`/`Màster`/`Especialitat` se conservan exactamente
  porque los usan el *entity linker* y el *scoping*); la jerarquía
  `subconcepteDe` se incluye en el contexto del LLM.
- **`ontology/fib_ontology.ttl`**: regenerado (1.434 tripletas, 13 clases,
  150 instancias; antes 126).
- **`evaluation/queries.json`**: la consulta «com demano un certificat de
  notes?» ahora acredita también la página específica
  `…/tramits/certificacions-academiques` como relevante (es la respuesta
  correcta; antes solo se aceptaba el índice genérico de trámites).

**No se ha tocado** el código de los retrievers (`controlled_ontology.py`,
`entity_linker.py`, `hybrid_rrf.py`, etc.): toda la mejora viene de los datos de
la ontología, gracias a que el re-ranqueo ya estaba diseñado para inyectar y
boostear cualquier recurso canónico que provenga del grafo.

## 4. Validación

- La consulta reportada devuelve ahora `/ca/mobilitat/dobles-titulacions` como
  **top-1** en modo `controlled`.
- Verificadas como top-1 también: grupos de recerca, biblioteca, gobierno,
  canvi de menció, trasllat d'expedient, simultaneïtat, universitats partner.
- **Sin regresión** en el golden set: `controlled` se mantiene en
  92,5 % Hit@5 / 0,82 MRR (global), 90 % en el split held-out.
- Sin falsos positivos en consultas de control (p.ej. «quina nota cal per
  entrar?» no dispara ningún concepto espurio).

## 5. Cómo regenerar

```bash
python3 scraper.py                        # scrape complet (graus + masters + assignatures)
python3 -m ontology.build_ontology      # regenera el .ttl
python3 ingest.py --from-scrape --reset  # reindexa ChromaDB
python3 -m evaluation.evaluate          # comprueba métricas
```

---

## 6. Ampliación del scraping e integración de assignatures de màster (jun 2026)

### Problema
Les assignatures de màster (i d'altres graus) no estaven indexades: el scraper només
scrapejava individualment la llista hardcodeada del GEI (~94 codis), mentre que les
pàgines índex de màster sí que existien però els enllaços individuals no es seguien.

### Canvis al scraper (`scraper.py`)
- **Seeds ampliats**: pàgines de matrícula/horaris/exàmens/pla d'estudis dels 4 masters
  FIB + GCED/GIA/BBIO + mobilitat (dobles titulacions, aliances), recerca, empresa, cita prèvia.
- **Descobriment dinàmic d'assignatures**: des de cada pàgina
  `…/pla-destudis/assignatures` (8 titulacions configurades) es descobreixen i scrapejen
  automàticament totes les assignatures individuals.
- Eliminada la llista hardcodeada de ~94 codis GEI (substituïda pel descobriment dinàmic).

**Resultat del scraping:**
| Abans | Després |
|-------|---------|
| ~1.573 documents | **4.021 documents** |
| 0 assignatures màster | **171 assignatures màster** |
| 101 assignatures GEI | **194 assignatures graus** (totes les titulacions) |
| ~951 pàgines | **951 pàgines**, 0 errors |

### Canvis a la ontologia (`build_ontology.py`)
- `_load_courses_from_scrape()`: extreu code, nom, URL i titulació (Grau/Màster) de qualsevol
  assignatura scrapejada.
- Després del bloc GEI (que conserva les relacions `dinsEspecialitat`), s'afegeixen
  automàticament les assignatures d'altres graus i masters amb `pertanyA` a la titulació correcta.
- **365 assignatures** a l'ontologia (abans 94), **421 instàncies** totals.

### Fix entity linker (`entity_linker.py`)
- Les sigles de titulació (MDS, MEI, MIRI…) ja no es disparen quan formen part d'un codi
  d'assignatura (p.ex. `MDS` dins `BSG-MDS`). Regex amb lookbehind `(?<![-\w])`.

### Indexació
- ChromaDB reindexat: **15.420 chunks** (abans ~2.700).
