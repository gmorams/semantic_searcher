"""
Scraper de fib.upc.edu. Descarga las secciones principales, parsea el HTML
y guarda los documentos resultantes en disco.
"""

import requests
import time
import json
import os
import sys
import re
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# ============================================================================
# CONFIGURACION
# ============================================================================

BASE_URL = "https://www.fib.upc.edu"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "scraped_data")
DELAY = 0.5  # respetar al servidor entre peticiones

HEADERS = {
    "User-Agent": "FIBot-TFG-Scraper/1.0 (Academic Research Project - UPC FIB)",
    "Accept-Language": "ca,es;q=0.9,en;q=0.8",
}

# secciones semilla, ordenadas por prioridad
SEED_URLS = [
    # Grado en Ingenieria Informatica (GEI)
    "/ca/graus/grau-en-enginyeria-informatica",
    "/ca/graus/grau-en-enginyeria-informatica/matricula",
    "/ca/graus/grau-en-enginyeria-informatica/pla-destudis",
    "/ca/graus/grau-en-enginyeria-informatica/pla-destudis/assignatures",
    "/ca/graus/grau-en-enginyeria-informatica/pla-destudis/especialitats",
    "/ca/graus/grau-en-enginyeria-informatica/horaris",
    "/ca/graus/grau-en-enginyeria-informatica/examens",
    "/ca/graus/grau-en-enginyeria-informatica/normativa-academica",
    "/ca/graus/grau-en-enginyeria-informatica/treball-de-fi-de-grau",
    "/ca/graus/grau-en-enginyeria-informatica/professorat",
    # otros grados
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/matricula",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/horaris",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/examens",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/pla-destudis",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/pla-destudis/assignatures",
    "/ca/graus/grau-en-intelligencia-artificial",
    "/ca/graus/grau-en-intelligencia-artificial/matricula",
    "/ca/graus/grau-en-intelligencia-artificial/horaris",
    "/ca/graus/grau-en-intelligencia-artificial/examens",
    "/ca/graus/grau-en-intelligencia-artificial/pla-destudis",
    "/ca/graus/grau-en-intelligencia-artificial/pla-destudis/assignatures",
    # Bioinformatica (grados interuniversitarios)
    "/ca/graus/grau-en-bioinformatica",
    "/ca/graus/grau-en-bioinformatica/pla-destudis",
    "/ca/graus/grau-en-bioinformatica/pla-destudis/assignatures",
    # Masters oficiales de la FIB
    "/ca/masters/master-en-enginyeria-informatica",
    "/ca/masters/master-en-enginyeria-informatica/matricula",
    "/ca/masters/master-en-enginyeria-informatica/horaris",
    "/ca/masters/master-en-enginyeria-informatica/examens",
    "/ca/masters/master-en-enginyeria-informatica/pla-destudis",
    "/ca/masters/master-en-enginyeria-informatica/pla-destudis/assignatures",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/matricula",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/horaris",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/examens",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/pla-destudis",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/pla-destudis/assignatures",
    "/ca/masters/master-en-ciencia-de-dades",
    "/ca/masters/master-en-ciencia-de-dades/matricula",
    "/ca/masters/master-en-ciencia-de-dades/horaris",
    "/ca/masters/master-en-ciencia-de-dades/examens",
    "/ca/masters/master-en-ciencia-de-dades/pla-destudis",
    "/ca/masters/master-en-ciencia-de-dades/pla-destudis/assignatures",
    "/ca/masters/master-en-intelligencia-artificial",
    "/ca/masters/master-en-intelligencia-artificial/matricula",
    "/ca/masters/master-en-intelligencia-artificial/horaris",
    "/ca/masters/master-en-intelligencia-artificial/examens",
    "/ca/masters/master-en-intelligencia-artificial/pla-destudis",
    "/ca/masters/master-en-intelligencia-artificial/pla-destudis/assignatures",
    # tramites y servicios
    "/ca/que-necessites/tramits",
    "/ca/que-necessites/cita-previa",
    "/ca/que-necessites/bustia-fib",
    # info general
    "/ca/la-fib",
    "/ca/la-fib/govern",
    "/ca/la-fib/associacions",
    "/ca/la-fib/la-facultat-en-xifres",
    "/ca/que-necessites",
    "/ca/que-necessites/calendaris-academics",
    "/ca/que-necessites/beques-i-ajuts",
    # movilidad
    "/ca/mobilitat",
    "/ca/mobilitat/dobles-titulacions",
    "/ca/mobilitat/aliances-internacionals",
    "/ca/mobilitat/aliances-internacionals/programes-de-mobilitat",
    "/ca/mobilitat/aliances-internacionals/universitats-partner",
    # investigacion
    "/ca/recerca",
    "/ca/recerca/departaments",
    "/ca/recerca/grups-de-recerca",
    "/ca/recerca/centres-de-recerca",
    "/ca/recerca/inlab-fib",
    # empresa
    "/ca/empresa",
]

# indices de asignaturas: de cada uno descubrimos dinamicamente todos los codigos.
ASSIG_INDEX_URLS = [
    "/ca/graus/grau-en-enginyeria-informatica/pla-destudis/assignatures",
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades/pla-destudis/assignatures",
    "/ca/graus/grau-en-intelligencia-artificial/pla-destudis/assignatures",
    "/ca/graus/grau-en-bioinformatica/pla-destudis/assignatures",
    "/ca/masters/master-en-enginyeria-informatica/pla-destudis/assignatures",
    "/ca/masters/master-en-innovacio-i-recerca-en-informatica/pla-destudis/assignatures",
    "/ca/masters/master-en-ciencia-de-dades/pla-destudis/assignatures",
    "/ca/masters/master-en-intelligencia-artificial/pla-destudis/assignatures",
]


# ============================================================================
# SCRAPER
# ============================================================================

class FIBScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.visited = set()
        self.documents = []
        self.failed = []
        os.makedirs(OUTPUT_DIR, exist_ok=True)

    def fetch(self, url):
        """Descarga una URL con reintentos."""
        full_url = url if url.startswith("http") else BASE_URL + url
        if full_url in self.visited:
            return None
        self.visited.add(full_url)

        for attempt in range(3):
            try:
                resp = self.session.get(full_url, timeout=15)
                if resp.status_code == 200:
                    time.sleep(DELAY)
                    return resp
                elif resp.status_code == 404:
                    return None
                else:
                    time.sleep(2)
            except Exception:
                time.sleep(2)
        self.failed.append(full_url)
        return None

    def parse_page(self, response, url):
        """Extrae el contenido principal de una pagina."""
        soup = BeautifulSoup(response.content, "html.parser")

        # titulo principal
        h1_tags = soup.find_all("h1")
        title = " ".join(t.get_text(strip=True) for t in h1_tags) if h1_tags else ""

        # probamos varios selectores y nos quedamos con el primero que tenga texto real
        candidates = [
            soup.find("div", id="section-main-content"),
            soup.find("div", id="content"),
            soup.find("div", role="main"),
            soup.find("article"),
            soup.find("main"),
            soup.find("body"),
        ]
        main = None
        for candidate in candidates:
            if candidate:
                text = candidate.get_text(strip=True)
                if len(text) > 50:
                    main = candidate
                    break

        if not main:
            return []

        # limpiamos scripts, estilos y elementos de navegacion
        for tag in main.find_all(["script", "style", "noscript"]):
            tag.decompose()
        for nav in main.find_all(["nav"]):
            nav.decompose()
        for sidebar in main.find_all("div", class_=lambda c: c and any(
            x in str(c).lower() for x in ["sidebar", "menu", "navigation", "breadcrumb", "block-menu"]
        )):
            sidebar.decompose()
        for aside in main.find_all("aside"):
            aside.decompose()

        sections = self._extract_sections(main, title, url)

        if not sections:
            # fallback: todo el texto en una unica seccion
            text = main.get_text(separator="\n", strip=True)
            if text and len(text) > 50:
                sections = [{
                    "title": title or self._title_from_url(url),
                    "content": text,
                    "url": url if url.startswith("http") else BASE_URL + url,
                    "section": "",
                }]

        return sections

    def _extract_sections(self, main_div, page_title, url):
        """Trocea el contenido por h2/h3."""
        full_url = url if url.startswith("http") else BASE_URL + url
        sections = []

        h2_tags = main_div.find_all("h2")

        if not h2_tags:
            # sin h2 devolvemos todo el bloque
            text = main_div.get_text(separator="\n", strip=True)
            if text and len(text) > 50:
                sections.append({
                    "title": page_title or self._title_from_url(url),
                    "content": text,
                    "url": full_url,
                    "section": "",
                })
            return sections

        # texto previo al primer h2
        pre_text = ""
        for sibling in main_div.children:
            if sibling == h2_tags[0]:
                break
            if hasattr(sibling, "get_text"):
                pre_text += sibling.get_text(separator="\n", strip=True) + "\n"
        if pre_text.strip() and len(pre_text.strip()) > 30:
            sections.append({
                "title": page_title or self._title_from_url(url),
                "content": pre_text.strip(),
                "url": full_url,
                "section": "Introduccio",
            })

        for h2 in h2_tags:
            section_title = h2.get_text(strip=True)
            section_text = ""
            for sibling in h2.find_next_siblings():
                if sibling.name == "h2":
                    break
                if hasattr(sibling, "get_text"):
                    section_text += sibling.get_text(separator="\n", strip=True) + "\n"

            if section_text.strip() and len(section_text.strip()) > 20:
                sections.append({
                    "title": f"{page_title} - {section_title}",
                    "content": section_text.strip(),
                    "url": full_url,
                    "section": section_title,
                })

        return sections

    def _title_from_url(self, url):
        """Titulo de respaldo a partir de la URL."""
        path = urlparse(url).path if url.startswith("http") else url
        parts = path.strip("/").split("/")
        if parts:
            return parts[-1].replace("-", " ").title()
        return "Document"

    def _discover_assignatures_from_index(self, index_url):
        """Descubre todas las URLs de asignaturas listadas en un indice de pla-destudis."""
        # peticion directa: no la marcamos como visitada porque la indice tambien sale en SEED
        full_url = index_url if index_url.startswith("http") else BASE_URL + index_url
        try:
            resp = self.session.get(full_url, timeout=15)
            if resp.status_code != 200:
                return set()
            time.sleep(DELAY)
        except Exception:
            return set()

        soup = BeautifulSoup(resp.content, "html.parser")
        prefix = index_url.rstrip("/") + "/"
        found = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # normaliza a path relativo
            if href.startswith(BASE_URL):
                href = href[len(BASE_URL):]
            if not href.startswith(prefix):
                continue
            tail = href[len(prefix):].strip("/")
            # solo nos interesa el primer segmento despues del prefijo
            if not tail or "/" in tail or "?" in tail or "#" in tail:
                continue
            # heuristica: los codigos de asignatura son cortos y alfanumericos en mayusculas
            if not re.match(r"^[A-Z0-9\-]{1,15}$", tail):
                continue
            found.add(prefix + tail)
        return found

    def discover_links(self, response, url):
        """Descubre enlaces internos relevantes en una pagina."""
        soup = BeautifulSoup(response.content, "html.parser")
        main = soup.find("div", id="section-main-content")
        if not main:
            main = soup.find("article") or soup.find("main") or soup

        links = set()
        for a in main.find_all("a", href=True):
            href = a["href"]
            # solo enlaces internos en catalan
            if href.startswith("/ca/"):
                full = BASE_URL + href
                if full not in self.visited and self._is_relevant(href):
                    links.add(href)
            elif href.startswith(BASE_URL + "/ca/"):
                if href not in self.visited and self._is_relevant(href):
                    links.add(href)
        return links

    def _is_relevant(self, url):
        """Descarta URLs ruidosas (redes sociales, assets, etc.)."""
        skip_patterns = [
            "/node/", "/user/", "/search", "/feed", "/print/",
            ".jpg", ".png", ".gif", ".svg", ".css", ".js",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "youtube.com", "flickr.com", "bsky.app",
        ]
        return not any(p in url.lower() for p in skip_patterns)

    def scrape_all(self, quick=False):
        """Ejecuta el scraping completo."""
        # 1. secciones semilla
        discovered_links = set()
        for seed_url in SEED_URLS:
            resp = self.fetch(seed_url)
            if resp:
                docs = self.parse_page(resp, seed_url)
                self.documents.extend(docs)
                new_links = self.discover_links(resp, seed_url)
                discovered_links.update(new_links)

        # 2. descubrimiento dinamico de asignaturas (grados + masters)
        all_assig_urls = set()
        for index_url in ASSIG_INDEX_URLS:
            assig_urls = self._discover_assignatures_from_index(index_url)
            all_assig_urls.update(assig_urls)

        for assig_url in sorted(all_assig_urls):
            resp = self.fetch(assig_url)
            if resp:
                docs = self.parse_page(resp, assig_url)
                self.documents.extend(docs)

        # 3. enlaces descubiertos (solo si no estamos en modo rapido)
        if not quick and discovered_links:
            for link in sorted(discovered_links):
                resp = self.fetch(link)
                if resp:
                    docs = self.parse_page(resp, link)
                    self.documents.extend(docs)

        self._save_results()
        return self.documents

    def _save_results(self):
        """Persiste los documentos y las estadisticas en disco."""
        output_file = os.path.join(OUTPUT_DIR, "fib_documents.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)

        stats = {
            "total_documents": len(self.documents),
            "pages_visited": len(self.visited),
            "failed_urls": self.failed,
            "urls_visited": sorted(self.visited),
        }
        stats_file = os.path.join(OUTPUT_DIR, "scrape_stats.json")
        with open(stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    quick = "--quick" in sys.argv
    scraper = FIBScraper()
    scraper.scrape_all(quick=quick)
    print(f"\n{'='*60}")
    print(f"  SCRAPING COMPLETAT!")
    print(f"  Documents obtinguts: {len(scraper.documents)}")
    print(f"  Pagines visitades:   {len(scraper.visited)}")
    print(f"  Errors:              {len(scraper.failed)}")
    print(f"  Dades guardades a:   {OUTPUT_DIR}/")
    print(f"{'='*60}")
    print(f"\nAra executa: python3 ingest.py --from-scrape")
