import fitz  # PyMuPDF
from typing import List, Dict
import re
import os


def load_and_chunk_pdf(pdf_path: str, chunk_size: int = 800, chunk_overlap: int = 200) -> List[Dict]:
    """
    Carrega un PDF, extreu el text, el divideix en seccions intel-ligents
    (basades en titols/headings) i retorna chunks amb metadades.
    """
    doc = fitz.open(pdf_path)
    filename = os.path.basename(pdf_path)

    # Extreure titol principal
    title = _extract_title(doc)

    # Extreure text complet amb deteccio de seccions
    sections = _extract_sections(doc)

    # Generar chunks a partir de les seccions
    chunks = []
    chunk_id = 0

    for section in sections:
        section_text = section["text"].strip()
        if not section_text or len(section_text) < 50:
            continue

        # Si la seccio es prou petita, un sol chunk
        if len(section_text) <= chunk_size:
            chunks.append({
                "id": f"{filename}_{chunk_id}",
                "text": section_text,
                "title": f"{title} - {section['heading']}" if section["heading"] else title,
                "source": pdf_path,
                "chunk_id": chunk_id,
                "section": section["heading"],
            })
            chunk_id += 1
        else:
            # Dividir seccions grans en chunks amb overlap
            start = 0
            while start < len(section_text):
                end = start + chunk_size
                chunk_text = section_text[start:end]

                if chunk_text.strip():
                    chunks.append({
                        "id": f"{filename}_{chunk_id}",
                        "text": chunk_text.strip(),
                        "title": f"{title} - {section['heading']}" if section["heading"] else title,
                        "source": pdf_path,
                        "chunk_id": chunk_id,
                        "section": section["heading"],
                    })
                    chunk_id += 1

                start = end - chunk_overlap

    return chunks


def _extract_title(doc) -> str:
    """Extreu el titol del PDF basat en la mida de font mes gran de la primera pagina."""
    for page in doc:
        blocks = page.get_text("dict")["blocks"]
        spans = []
        for block in blocks:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text and len(text) > 2:
                            spans.append((span["size"], text))
        if spans:
            max_size = max(s[0] for s in spans)
            title_parts = [t for s, t in spans if abs(s - max_size) < 1.0]
            if title_parts:
                return " ".join(title_parts)
        break  # Nomes primera pagina
    return "Document"


def _extract_sections(doc) -> List[Dict]:
    """Extreu seccions del PDF detectant titols per mida de font."""
    full_text = ""
    for page in doc:
        full_text += page.get_text() + "\n"

    # Detectar seccions amb regex (titols numerats, majuscules, etc.)
    section_pattern = r'(?P<title>\n\d+\.[\d.]*\s+[A-ZÀ-ÿ][^\n]{3,})\n'
    matches = list(re.finditer(section_pattern, full_text))

    if not matches:
        # Fallback: retornar tot el text com una sola seccio
        return [{"heading": "", "text": full_text}]

    sections = []

    # Text abans de la primera seccio
    pre_text = full_text[:matches[0].start()].strip()
    if pre_text and len(pre_text) > 100:
        sections.append({"heading": "Introducció", "text": pre_text})

    for i, match in enumerate(matches):
        heading = match.group("title").strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
        text = full_text[start:end].strip()

        if text:
            sections.append({"heading": heading, "text": text})

    return sections
