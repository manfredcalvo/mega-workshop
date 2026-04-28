# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
Megacable Enterprise Solutions Web Scraper
Scrapes all 8 enterprise solution categories from mcmtechco.com/soluciones
and outputs markdown files suitable for Databricks Knowledge Assistant ingestion.

Expects Databricks notebook widget parameters:
  - uc_catalog: Unity Catalog catalog name
  - uc_schema: Unity Catalog schema name
  - uc_volume: Unity Catalog volume name
Output is written to /Volumes/<catalog>/<schema>/<volume>/output_solutions/
"""

import os
import re
import time
import requests
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin

# Read UC volume config from notebook widget parameters
dbutils.widgets.text("uc_catalog", "", "UC Catalog")
dbutils.widgets.text("uc_schema", "", "UC Schema")
dbutils.widgets.text("uc_volume", "", "UC Volume")

uc_catalog = dbutils.widgets.get("uc_catalog")
uc_schema = dbutils.widgets.get("uc_schema")
uc_volume = dbutils.widgets.get("uc_volume")

BASE_URL = "https://www.mcmtechco.com"
CATALOG_URL = f"{BASE_URL}/soluciones/"
OUTPUT_DIR = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_solutions"
REQUEST_DELAY = 2  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
}

SOLUTIONS = [
    {
        "name": "[Hiper] Conectividad",
        "slug": "hiperconectividad-empresarial",
        "url": f"{BASE_URL}/soluciones/hiperconectividad-empresarial",
        "description": "Conectividad al siguiente nivel con soluciones integrales que garantizan una red segura, estable y eficiente.",
    },
    {
        "name": "Colaboración | Symphony",
        "slug": "symphony",
        "url": f"{BASE_URL}/soluciones/symphony",
        "description": "Plataforma unificada de comunicaciones, colaboración y contact center como servicio (UCaaS y CCaaS).",
    },
    {
        "name": "Ciberseguridad",
        "slug": "ciberseguridad-empresarial",
        "url": f"{BASE_URL}/soluciones/ciberseguridad-empresarial",
        "description": "Protege la infraestructura, los datos y las operaciones de tu empresa con tecnología avanzada.",
    },
    {
        "name": "Nube | [Hiper] Convergencia",
        "slug": "hiperconvergencia-empresarial",
        "url": f"{BASE_URL}/soluciones/hiperconvergencia-empresarial",
        "description": "Infraestructura hiperconvergente que proporciona la configuración óptima para cargas de trabajo críticas.",
    },
    {
        "name": "Megacable Data Center",
        "slug": "megacable-data-center",
        "url": f"{BASE_URL}/soluciones/megacable-data-center",
        "description": "Servicios de data center que combinan innovación con excelencia operativa.",
    },
    {
        "name": "Seguridad Física",
        "slug": "seguridad-fisica",
        "url": f"{BASE_URL}/soluciones/seguridad-fisica",
        "description": "Protege tus instalaciones, activos y personal con tecnología avanzada de videovigilancia y control de accesos.",
    },
    {
        "name": "Infraestructura como Servicio",
        "slug": "infraestructura-como-servicio",
        "url": f"{BASE_URL}/soluciones/",
        "description": "Soluciones de infraestructura administrada con énfasis en escalabilidad y optimización operativa.",
    },
    {
        "name": "Carriers",
        "slug": "carriers",
        "url": f"{BASE_URL}/soluciones/carriers",
        "description": "Soluciones de conectividad mayorista: Wavelength y frecuencias de 23 GHz.",
    },
]


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a page and return a BeautifulSoup object."""
    print(f"  Fetching: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return BeautifulSoup(resp.text, "html.parser")


def absolute_url(href: str) -> str:
    """Convert a relative URL to absolute."""
    if not href:
        return ""
    if href.startswith("http"):
        return href
    return urljoin(BASE_URL, href)


def _inline_to_md(element) -> str:
    """Convert inline HTML to markdown, preserving <a> links and formatting."""
    if element is None:
        return ""

    parts = []
    for child in element.children:
        if isinstance(child, NavigableString):
            text = str(child).strip()
            if text:
                parts.append(text)
        elif child.name == "a":
            href = absolute_url(child.get("href", ""))
            text = child.get_text(strip=True)
            if text and href:
                parts.append(f"[{text}]({href})")
            elif text:
                parts.append(text)
        elif child.name in ("strong", "b"):
            inner = _inline_to_md(child)
            if inner:
                parts.append(f"**{inner}**")
        elif child.name in ("em", "i"):
            inner = _inline_to_md(child)
            if inner:
                parts.append(f"*{inner}*")
        elif child.name == "br":
            parts.append("\n")
        elif child.name == "ul":
            for li in child.find_all("li", recursive=False):
                li_text = _inline_to_md(li)
                if li_text:
                    parts.append(f"\n- {li_text}")
        elif child.name == "ol":
            for i, li in enumerate(child.find_all("li", recursive=False), 1):
                li_text = _inline_to_md(li)
                if li_text:
                    parts.append(f"\n{i}. {li_text}")
        else:
            inner = _inline_to_md(child)
            if inner:
                parts.append(inner)

    return " ".join(parts).replace("  ", " ").strip()


def _table_to_md(table_elem) -> str:
    """Convert an HTML table to markdown."""
    rows = []
    for tr in table_elem.find_all("tr"):
        cells = []
        for td in tr.find_all(["td", "th"]):
            cells.append(_inline_to_md(td).replace("|", "\\|"))
        rows.append(cells)

    if not rows:
        return ""

    max_cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < max_cols:
            r.append("")

    lines = []
    lines.append("| " + " | ".join(rows[0]) + " |")
    lines.append("| " + " | ".join(["---"] * max_cols) + " |")
    for row in rows[1:]:
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


def extract_text_blocks(soup: BeautifulSoup) -> list[str]:
    """Extract meaningful text blocks from a page, avoiding nav/footer/script noise."""
    lines = []
    seen = set()

    # Remove script, style, nav, footer, header elements
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript"]):
        tag.decompose()

    main = soup.find("main") or soup.find(id="main") or soup.find(class_=re.compile(r"main|content|body"))
    container = main if main else soup.body

    if not container:
        return lines

    for elem in container.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "td", "th"]):
        text = elem.get_text(separator=" ", strip=True)
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) < 5 or text in seen:
            continue
        seen.add(text)

        tag = elem.name
        if tag == "h1":
            lines.append(f"\n# {text}\n")
        elif tag == "h2":
            lines.append(f"\n## {text}\n")
        elif tag == "h3":
            lines.append(f"\n### {text}\n")
        elif tag in ("h4", "h5", "h6"):
            lines.append(f"\n#### {text}\n")
        elif tag == "li":
            lines.append(f"- {text}")
        else:
            lines.append(text)

    return lines


def scrape_solution_page(solution: dict) -> str:
    """Scrape a single solution page and return its markdown content."""
    sections = []
    sections.append(f"# {solution['name']}\n")
    sections.append(f"**{solution['description']}**\n")
    sections.append(f"**URL:** {solution['url']}\n")
    sections.append("---\n")

    try:
        soup = fetch_page(solution["url"])
        blocks = extract_text_blocks(soup)
        if blocks:
            sections.extend(blocks)
        else:
            sections.append("_(No se pudo extraer contenido adicional de esta página.)_\n")
    except Exception as e:
        print(f"    WARNING: Could not scrape {solution['url']}: {e}")
        sections.append(f"_(Error al obtener el contenido: {e})_\n")

    return "\n".join(sections)


def build_catalog_overview() -> str:
    """Build a markdown overview of all Megacable enterprise solutions."""
    lines = [
        "# Catálogo de Soluciones Empresariales Megacable\n",
        "Megacable ofrece un portafolio integral de soluciones tecnológicas para empresas, "
        "diseñadas para impulsar la conectividad, seguridad, colaboración y eficiencia operativa.\n",
        f"**Sitio web:** {CATALOG_URL}\n",
        "---\n",
        "## Soluciones Disponibles\n",
    ]

    for sol in SOLUTIONS:
        lines.append(f"### {sol['name']}")
        lines.append(f"{sol['description']}")
        lines.append(f"**Más información:** {sol['url']}\n")

    return "\n".join(lines)


def scrape_all_solutions():
    """Main function: scrape catalog overview and all 8 solution pages."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("Megacable Enterprise Solutions Scraper")
    print("=" * 60)

    # Step 1: Save catalog overview
    print("\n[1/2] Building catalog overview...")
    overview_md = build_catalog_overview()
    overview_path = os.path.join(OUTPUT_DIR, "catalogo-soluciones-megacable.md")
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(overview_md)
    print(f"  -> Saved catalog overview to {overview_path}")

    # Step 2: Scrape each solution page
    print(f"\n[2/2] Scraping {len(SOLUTIONS)} solution pages...\n")
    for i, solution in enumerate(SOLUTIONS, 1):
        print(f"  [{i}/{len(SOLUTIONS)}] {solution['name']}")
        try:
            markdown = scrape_solution_page(solution)
            filename = f"{solution['slug']}.md"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"    -> Saved to {filepath}")
        except Exception as e:
            print(f"    ERROR: {e}")

        if i < len(SOLUTIONS):
            time.sleep(REQUEST_DELAY)

    print(f"\nDone! Files saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    scrape_all_solutions()
