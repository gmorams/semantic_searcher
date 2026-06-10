"""
Crawler/Scraper de fib.upc.edu
Recorre les seccions principals de la web de la FIB,
descarrega el contingut HTML, el parseja i el guarda com a documents nets.

Us:
    python3 scraper.py              # Scrape complet
    python3 scraper.py --quick      # Nomes seccions principals (mes rapid)
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
# CONFIGURACIO
# ============================================================================

BASE_URL = "https://www.fib.upc.edu"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "scraped_data")
DELAY = 0.5  # Respectar el servidor

HEADERS = {
    "User-Agent": "FIBot-TFG-Scraper/1.0 (Academic Research Project - UPC FIB)",
    "Accept-Language": "ca,es;q=0.9,en;q=0.8",
}

# Seccions a scrapejar amb prioritat
SEED_URLS = [
    # Grau en Enginyeria Informatica
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
    # Altres graus
    "/ca/graus/grau-en-ciencia-i-enginyeria-de-dades",
    "/ca/graus/grau-en-intelligencia-artificial",
    # Tramits
    "/ca/que-necessites/tramits",
    # Info general
    "/ca/la-fib",
    "/ca/que-necessites",
    "/ca/que-necessites/calendaris-academics",
    "/ca/que-necessites/beques-i-ajuts",
    # Mobilitat
    "/ca/mobilitat",
]

# Assignatures del GEI (les scrapegem totes individualment)
ASSIGNATURES = [
    "F", "FM", "IC", "PRO1", "EC", "M1", "M2", "PRO2",
    "BD", "CI", "EDA", "PE", "SO", "AC", "EEE", "IES", "PROP", "XC", "IDI", "PAR",
    # Computacio
    "A", "G", "IA", "LI", "LP", "TC", "AA", "APA", "CAIM", "CL", "CN", "IO", "SID",
    # Eng. Computadors
    "AC2", "DSBM", "MP", "PEC", "SO2", "XC2", "CASO", "CPD", "PAP", "PCA", "PDS", "STR", "VLSI",
    # Eng. Software
    "AS", "ASW", "DBD", "ER", "GPS", "PES", "CAP", "CBDE", "CSI", "ECSDI", "SIM", "SOAD",
    # Sistemes d'Informacio
    "ADEI", "DSI", "NE", "PSI", "SIO", "ABD", "EDO", "MI", "VPE", "MD",
    # Tecnologies de la Informacio
    "ASO", "PI", "PTI", "SI", "SOA", "TXC", "AD", "IM", "SDX", "TCI",
    # Optatives
    "APC", "ASMI", "C", "CCQ", "CDI", "DCS", "EET", "GCS", "GEOC",
    "LDPE", "PAE", "ROB", "SLDS", "TGA", "VC", "VJ",
]

ASSIG_URL_TEMPLATE = "/ca/graus/grau-en-enginyeria-informatica/pla-destudis/assignatures/{}"


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
        """Descarrega una URL amb retry."""
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
                    print(f"  [404] {full_url}")
                    return None
                else:
                    print(f"  [{resp.status_code}] {full_url} (retry {attempt+1})")
                    time.sleep(2)
            except Exception as e:
                print(f"  [ERROR] {full_url}: {e} (retry {attempt+1})")
                time.sleep(2)
        self.failed.append(full_url)
        return None

    def parse_page(self, response, url):
        """Parseja una pagina HTML i extreu el contingut principal."""
        soup = BeautifulSoup(response.content, "html.parser")

        # Titol principal
        h1_tags = soup.find_all("h1")
        title = " ".join(t.get_text(strip=True) for t in h1_tags) if h1_tags else ""

        # Provar multiples selectors per trobar el contingut principal
        # Prioritzar els que tenen mes text real
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

        # Extreure tot el text net (sense scripts/styles/navs)
        for tag in main.find_all(["script", "style", "noscript"]):
            tag.decompose()
        # Eliminar menus de navegacio laterals i breadcrumbs
        for nav in main.find_all(["nav"]):
            nav.decompose()
        for sidebar in main.find_all("div", class_=lambda c: c and any(
            x in str(c).lower() for x in ["sidebar", "menu", "navigation", "breadcrumb", "block-menu"]
        )):
            sidebar.decompose()
        for aside in main.find_all("aside"):
            aside.decompose()

        # Extreure seccions per h2
        sections = self._extract_sections(main, title, url)

        if not sections:
            # Fallback: agafar tot el text
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
        """Divideix el contingut en seccions basades en h2/h3."""
        full_url = url if url.startswith("http") else BASE_URL + url
        sections = []

        h2_tags = main_div.find_all("h2")

        if not h2_tags:
            # Sense h2: retornar tot com una sola seccio
            text = main_div.get_text(separator="\n", strip=True)
            if text and len(text) > 50:
                sections.append({
                    "title": page_title or self._title_from_url(url),
                    "content": text,
                    "url": full_url,
                    "section": "",
                })
            return sections

        # Text abans del primer h2
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

        # Seccions h2
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
        """Genera un titol a partir de la URL."""
        path = urlparse(url).path if url.startswith("http") else url
        parts = path.strip("/").split("/")
        if parts:
            return parts[-1].replace("-", " ").title()
        return "Document"

    def discover_links(self, response, url):
        """Descobreix links interns rellevants dins una pagina."""
        soup = BeautifulSoup(response.content, "html.parser")
        main = soup.find("div", id="section-main-content")
        if not main:
            main = soup.find("article") or soup.find("main") or soup

        links = set()
        for a in main.find_all("a", href=True):
            href = a["href"]
            # Nomes links interns de la FIB en catala
            if href.startswith("/ca/"):
                full = BASE_URL + href
                if full not in self.visited and self._is_relevant(href):
                    links.add(href)
            elif href.startswith(BASE_URL + "/ca/"):
                if href not in self.visited and self._is_relevant(href):
                    links.add(href)
        return links

    def _is_relevant(self, url):
        """Filtra URLs no rellevants."""
        skip_patterns = [
            "/node/", "/user/", "/search", "/feed", "/print/",
            ".jpg", ".png", ".gif", ".svg", ".css", ".js",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "youtube.com", "flickr.com", "bsky.app",
        ]
        return not any(p in url.lower() for p in skip_patterns)

    def scrape_all(self, quick=False):
        """Executa el scraping complet."""
        print(f"{'='*60}")
        print(f"  SCRAPING DE fib.upc.edu")
        print(f"{'='*60}\n")

        # 1. Seccions principals (seeds)
        print("1. Scrapejant seccions principals...")
        discovered_links = set()
        for i, seed_url in enumerate(SEED_URLS):
            print(f"  [{i+1}/{len(SEED_URLS)}] {seed_url}")
            resp = self.fetch(seed_url)
            if resp:
                docs = self.parse_page(resp, seed_url)
                self.documents.extend(docs)
                # Descobrir links addicionals
                new_links = self.discover_links(resp, seed_url)
                discovered_links.update(new_links)

        print(f"\n  -> {len(self.documents)} documents de seccions principals")
        print(f"  -> {len(discovered_links)} links addicionals descoberts\n")

        # 2. Assignatures individuals
        print("2. Scrapejant assignatures del GEI...")
        for i, assig in enumerate(ASSIGNATURES):
            url = ASSIG_URL_TEMPLATE.format(assig)
            if i % 10 == 0:
                print(f"  [{i+1}/{len(ASSIGNATURES)}] Processant assignatures...")
            resp = self.fetch(url)
            if resp:
                docs = self.parse_page(resp, url)
                self.documents.extend(docs)

        print(f"\n  -> {len(self.documents)} documents totals amb assignatures\n")

        # 3. Links descoberts (si no quick mode)
        if not quick and discovered_links:
            print(f"3. Scrapejant {len(discovered_links)} links addicionals descoberts...")
            for i, link in enumerate(sorted(discovered_links)):
                if i % 20 == 0:
                    print(f"  [{i+1}/{len(discovered_links)}] Processant links...")
                resp = self.fetch(link)
                if resp:
                    docs = self.parse_page(resp, link)
                    self.documents.extend(docs)

        # 4. Guardar resultats
        self._save_results()

        print(f"\n{'='*60}")
        print(f"  SCRAPING COMPLETAT!")
        print(f"  Documents obtinguts: {len(self.documents)}")
        print(f"  Pagines visitades:   {len(self.visited)}")
        print(f"  Errors:              {len(self.failed)}")
        print(f"  Dades guardades a:   {OUTPUT_DIR}/")
        print(f"{'='*60}")

        return self.documents

    def _save_results(self):
        """Guarda els documents scrapejats a disc."""
        output_file = os.path.join(OUTPUT_DIR, "fib_documents.json")
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(f"\n  Guardat a {output_file}")

        # Stats
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
    print(f"\nAra executa: python3 ingest.py --from-scrape")
