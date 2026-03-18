# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
BCP Loans/Credits Web Scraper
Scrapes loan product details from viabcp.com and outputs markdown files
suitable for Databricks Knowledge Assistant ingestion.

The loans section has a hierarchy:
  - Catalog pages (credito-efectivo, credito-hipotecario, credito-vehicular)
    that list sub-products
  - Detail pages (prestamo-personal, hipotecario/tradicional, etc.)
    with tabs, rates, docs
  - Standalone product pages (adelanto-de-sueldo, prestamo-tarjetero, etc.)

Expects Databricks notebook widget parameters:
  - uc_catalog: Unity Catalog catalog name
  - uc_schema: Unity Catalog schema name
  - uc_volume: Unity Catalog volume name
Output is written to /Volumes/<catalog>/<schema>/<volume>/output_loans/
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

BASE_URL = "https://www.viabcp.com"
OUTPUT_DIR = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_loans"
REQUEST_DELAY = 2

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
}

# Full product tree: (name, slug, url, sub_products)
# sub_products is a list of (name, slug, url) for catalog pages
LOAN_PRODUCTS = [
    {
        "name": "Crédito Efectivo Rápido",
        "slug": "credito-efectivo",
        "url": "/creditos/credito-efectivo",
        "is_catalog": True,
        "sub_products": [
            ("Préstamo Personal BCP", "prestamo-personal-bcp",
             "/creditos/credito-efectivo/prestamo-personal-bcp"),
            ("Préstamo con Garantía Hipotecaria", "garantia-hipotecaria",
             "/creditos/credito-efectivo/garantia-hipotecaria"),
            ("Préstamo Hipotecario Compartido", "garantia-hipotecaria-compartida",
             "/creditos/credito-efectivo/garantia-hipotecaria-compartida"),
            ("Préstamo con Garantía Líquida", "garantia-liquida",
             "/creditos/credito-efectivo/garantia-liquida"),
        ],
    },
    {
        "name": "Créditos Hipotecarios",
        "slug": "credito-hipotecario",
        "url": "/creditos/credito-hipotecario",
        "is_catalog": True,
        "sub_products": [
            ("Crédito Hipotecario Tradicional", "hipotecario-tradicional",
             "/creditos/credito-hipotecario/tradicional"),
            ("Crédito Hipotecario MiVivienda", "hipotecario-mivivienda",
             "/creditos/credito-hipotecario/nuevo-credito-mivivienda"),
            ("Crédito Hipotecario Ahorro Local", "hipotecario-ahorro-local",
             "/creditos/credito-hipotecario/ahorro-local-fondeo-bcp"),
            ("Crédito Hipotecario MiVivienda Alquileres", "hipotecario-mivivienda-alquileres",
             "/creditos/credito-hipotecario/nuevo-credito-mivivienda/ahorro-local"),
            ("Crédito Hipotecario Compartido", "hipotecario-compartido",
             "/creditos/credito-hipotecario/hipotecario-compartido"),
        ],
    },
    {
        "name": "Créditos Vehiculares",
        "slug": "credito-vehicular",
        "url": "/creditos/credito-vehicular",
        "is_catalog": True,
        "sub_products": [
            ("Crédito Vehicular Inteligente", "vehicular-inteligente",
             "/creditos/credito-vehicular/compra-inteligente"),
            ("Crédito Vehicular Tradicional", "vehicular-tradicional",
             "/creditos/credito-vehicular/tradicional"),
            ("Crédito Auto Usado", "vehicular-autousado",
             "/creditos/credito-vehicular/vehicular-autousado"),
        ],
    },
    {
        "name": "Adelanto de Sueldo",
        "slug": "adelanto-de-sueldo",
        "url": "/creditos/otros-creditos/adelanto-de-sueldo",
        "is_catalog": False,
        "sub_products": [],
    },
    {
        "name": "Yape Créditos",
        "slug": "creditos-yape",
        "url": "/canales/yape/creditos-yape",
        "is_catalog": False,
        "sub_products": [],
    },
    {
        "name": "Cuotéalo sin Tarjeta",
        "slug": "cuotealo",
        "url": "/cuotealo",
        "is_catalog": False,
        "sub_products": [],
    },
    {
        "name": "Préstamo Tarjetero",
        "slug": "prestamo-tarjetero",
        "url": "/creditos/otros-creditos/prestamo-tarjetero",
        "is_catalog": False,
        "sub_products": [],
    },
    {
        "name": "Préstamo Tarjetero Digital",
        "slug": "prestamo-tarjetero-digital",
        "url": "/prestamo-tarjetero-digital",
        "is_catalog": False,
        "sub_products": [],
    },
    {
        "name": "Crédito Estudiantil",
        "slug": "credito-de-estudio",
        "url": "/creditos/otros-creditos/credito-de-estudio",
        "is_catalog": False,
        "sub_products": [],
    },
]


def fetch_page(url: str) -> BeautifulSoup:
    """Fetch a page and return a BeautifulSoup object."""
    full_url = url if url.startswith("http") else f"{BASE_URL}{url}"
    print(f"  Fetching: {full_url}")
    resp = requests.get(full_url, headers=HEADERS, timeout=30)
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
    """Convert inline HTML to markdown, preserving links and formatting."""
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


def extract_rich_text(container) -> str:
    """Extract rich text from a container, preserving links and structure."""
    if container is None:
        return ""

    lines = []

    for elem in container.children:
        if isinstance(elem, NavigableString):
            text = elem.strip()
            if text:
                lines.append(text)
            continue

        if not hasattr(elem, "name"):
            continue

        if elem.name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(elem.name[1])
            prefix = "#" * (level + 1)
            lines.append(f"\n{prefix} {elem.get_text(strip=True)}\n")

        elif elem.name == "ul":
            for li in elem.find_all("li", recursive=False):
                li_text = _inline_to_md(li)
                if li_text:
                    lines.append(f"- {li_text}")

        elif elem.name == "ol":
            for i, li in enumerate(elem.find_all("li", recursive=False), 1):
                li_text = _inline_to_md(li)
                if li_text:
                    lines.append(f"{i}. {li_text}")

        elif elem.name == "table":
            lines.append(_table_to_md(elem))

        elif elem.name in ("p", "div"):
            if elem.find("svg"):
                continue
            text = _inline_to_md(elem)
            if text:
                lines.append(text)

        elif elem.name == "a":
            href = absolute_url(elem.get("href", ""))
            text = elem.get_text(strip=True)
            if text and href:
                lines.append(f"[{text}]({href})")
            elif text:
                lines.append(text)

        else:
            text = _inline_to_md(elem)
            if text:
                lines.append(text)

    return "\n".join(lines)


def _extract_document_links(container) -> list[tuple[str, str]]:
    """Extract PDF/document download links from a container."""
    links = []
    seen = set()
    for a in container.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not text or not href:
            continue
        if ".pdf" in href.lower() or "/wcm/connect/" in href or ".xls" in href.lower():
            full_url = absolute_url(href)
            if full_url not in seen:
                seen.add(full_url)
                links.append((text, full_url))
    return links


# ─── Catalog page extraction ───────────────────────────────────────

def extract_catalog_page(soup: BeautifulSoup, product: dict) -> str:
    """Extract content from a catalog page that lists sub-products."""
    sections = []

    # Title
    card_name = product["name"]
    tagline = ""

    # Try multiple banner patterns
    banner = soup.find(class_=re.compile(r"bcp-banner-interno|bcp_banner-sin-carousel"))
    if banner:
        title_el = (
            banner.find(class_="bcp-titulo")
            or banner.find(class_="banner_titulo")
            or banner.find("h1")
        )
        if title_el:
            card_name = title_el.get_text(strip=True)

        desc_el = (
            banner.find(class_="bcp-descripcion")
            or banner.find(class_="banner_subtitle")
        )
        if desc_el:
            tagline = desc_el.get_text(strip=True)

    if not tagline:
        h1 = soup.find("h1")
        if h1:
            card_name = h1.get_text(strip=True)

    sections.append(f"# {card_name}\n")
    if tagline:
        sections.append(f"**{tagline}**\n")

    sections.append(f"**Página:** {absolute_url(product['url'])}\n")
    sections.append("---\n")

    # Sub-products listed as boxes
    boxes = soup.find(class_=re.compile(
        r"bcp_boxes_tablero|bcp_listado_componente_boxes"
    ))
    if boxes:
        sections.append("## Productos\n")
        items = boxes.find_all(class_=re.compile(
            r"bcp_comp_box_tablero|bcp_contenedor_detalle_box"
        ))
        for item in items:
            title_el = item.find(class_=re.compile(r"bcp_titulo_box|titulo"))
            title = title_el.get_text(strip=True) if title_el else ""

            # Get feature bullets
            bullets = item.find_all("li")
            features = [li.get_text(strip=True) for li in bullets if li.get_text(strip=True)]

            # Get link
            link_el = item.find("a", href=True)
            href = absolute_url(link_el["href"]) if link_el else ""

            if title:
                if href:
                    sections.append(f"### [{title}]({href})\n")
                else:
                    sections.append(f"### {title}\n")
                for feat in features:
                    sections.append(f"- {feat}")
                sections.append("")

    # FAQ
    _extract_faq(soup, sections)

    return "\n".join(sections)


# ─── Detail page extraction ────────────────────────────────────────

def extract_detail_page(soup: BeautifulSoup, name: str, url: str) -> str:
    """Extract content from a product detail page."""
    sections = []

    # 1. Title and tagline
    card_name = name
    tagline = ""

    banner = soup.find(class_=re.compile(
        r"bcp-banner-interno|bcp_banner-sin-carousel|bcp_banner_principal"
    ))
    if banner:
        title_el = (
            banner.find(class_="bcp-titulo")
            or banner.find(class_="banner_titulo")
            or banner.find("h1")
        )
        if title_el:
            card_name = title_el.get_text(strip=True)

        desc_el = (
            banner.find(class_="bcp-descripcion")
            or banner.find(class_="banner_subtitle")
        )
        if desc_el:
            tagline = desc_el.get_text(strip=True)

    # Fallback to h1
    if card_name == name:
        h1 = soup.find("h1")
        if h1:
            card_name = h1.get_text(strip=True)

    sections.append(f"# {card_name}\n")
    if tagline:
        sections.append(f"**{tagline}**\n")

    sections.append(f"**Página:** {absolute_url(url)}\n")

    # Application links
    apply_links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if any(kw in href for kw in ["dineroalinstante", "mitarjetabcp", "bmo-para-ti"]):
            apply_links.append(href)
            break
    if apply_links:
        sections.append(f"**Solicítalo aquí:** {apply_links[0]}\n")

    sections.append("---\n")

    # 2. Benefit highlights
    _extract_benefit_highlights(soup, sections)

    # 3. Sub-product boxes (some detail pages also list variants)
    _extract_product_boxes(soup, sections)

    # 4. Tutorial steps
    _extract_tutorial_steps(soup, sections)

    # 5. Tabs section
    _extract_tabs(soup, sections)

    # 6. FAQ
    _extract_faq(soup, sections)

    return "\n".join(sections)


def _extract_benefit_highlights(soup: BeautifulSoup, sections: list):
    """Extract the benefit highlights section."""
    benefits_section = soup.find(class_="bcp_beneficio_presentacion_producto")
    if not benefits_section:
        return

    sections.append("## Beneficios Destacados\n")

    benefit_items = benefits_section.find_all(
        class_=lambda c: c and "bcp_beneficio_componente" in c
        and "titulo" not in c and "subtitulo" not in c
    )

    seen_benefits = set()
    for item in benefit_items:
        title_el = item.find(class_=re.compile(r"titulo"))
        subtitle_el = item.find(class_=re.compile(r"subtitulo"))

        title = title_el.get_text(strip=True) if title_el else ""
        desc = _inline_to_md(subtitle_el) if subtitle_el else ""

        # Deduplicate responsive copies
        key = (title, desc)
        if key in seen_benefits or not title:
            continue
        seen_benefits.add(key)

        if desc:
            sections.append(f"- **{title}:** {desc}")
        else:
            sections.append(f"- **{title}**")

    sections.append("\n---\n")


def _extract_product_boxes(soup: BeautifulSoup, sections: list):
    """Extract product boxes (for pages that list sub-variants)."""
    boxes = soup.find(class_=re.compile(
        r"bcp_boxes_tablero_con_boton|bcp_boxes_tablero_sin_boton"
    ))
    if not boxes:
        return

    items = boxes.find_all(class_=re.compile(r"bcp_comp_box_tablero"))
    if not items:
        return

    sections.append("## Opciones Disponibles\n")

    for item in items:
        title_el = item.find(class_=re.compile(r"bcp_titulo_box|titulo"))
        title = title_el.get_text(strip=True) if title_el else ""

        bullets = item.find_all("li")
        features = [li.get_text(strip=True) for li in bullets if li.get_text(strip=True)]

        link_el = item.find("a", href=True)
        href = absolute_url(link_el["href"]) if link_el else ""

        if title:
            if href:
                sections.append(f"### [{title}]({href})\n")
            else:
                sections.append(f"### {title}\n")
            for feat in features:
                sections.append(f"- {feat}")
            sections.append("")

    sections.append("---\n")


def _extract_tutorial_steps(soup: BeautifulSoup, sections: list):
    """Extract the tutorial/steps carousel."""
    tutorial = soup.find(class_="bcp_tutorial_tab_carousel")
    if not tutorial:
        return

    sections.append("## Cómo Obtenerlo\n")

    slides = tutorial.find_all(class_="bcp_slide_item_tab")
    if not slides:
        slides = tutorial.find_all(class_="swiper-slide")

    seen_steps = set()
    step_num = 0

    for slide in slides:
        title_el = slide.find(class_="bcp_titulo")
        desc_el = slide.find(class_=re.compile(r"bcp_descripcion"))

        title = title_el.get_text(strip=True) if title_el else ""
        desc = desc_el.get_text(strip=True) if desc_el else ""

        step_key = (title, desc)
        if step_key in seen_steps or not title:
            continue
        seen_steps.add(step_key)

        step_num += 1
        if desc:
            sections.append(f"{step_num}. **{title}** — {desc}")
        else:
            sections.append(f"{step_num}. **{title}**")

    sections.append("\n---\n")


def _extract_tabs(soup: BeautifulSoup, sections: list):
    """Extract the tabbed content section."""
    tabs_container = soup.find(class_=re.compile(r"bcp_todo_lo_que_debes_saber"))
    if not tabs_container:
        return

    tab_buttons = tabs_container.find_all(class_="bcp_tab_button")
    tab_names = [b.get_text(strip=True) for b in tab_buttons]

    tab_panels = tabs_container.find_all(class_="bcp_tab_componente_TIDS3")

    for idx, panel in enumerate(tab_panels):
        tab_name = tab_names[idx] if idx < len(tab_names) else f"Sección {idx + 1}"

        content_text = extract_rich_text(panel)
        if not content_text.strip():
            continue

        sections.append(f"## {tab_name}\n")
        sections.append(content_text)

        # Document links for Documentación tab
        if "documentac" in tab_name.lower():
            doc_links = _extract_document_links(panel)
            if doc_links:
                sections.append("\n### Documentos Descargables\n")
                for label, href in doc_links:
                    sections.append(f"- [{label}]({href})")

        sections.append("\n---\n")


def _extract_faq(soup: BeautifulSoup, sections: list):
    """Extract FAQ accordion items."""
    faq_section = soup.find(class_="bcp_preguntas_frecuentes_sin_categorias")
    if not faq_section:
        return

    accordion_wraps = faq_section.find_all(class_="accordion-wrap")
    if not accordion_wraps:
        return

    sections.append("## Preguntas Frecuentes\n")

    for wrap in accordion_wraps:
        header = wrap.find(class_="accordion-header")
        question = ""
        if header:
            h2 = header.find("h2")
            question = h2.get_text(strip=True) if h2 else header.get_text(strip=True)

        answer_el = wrap.find(class_="accordion-text")
        answer = ""
        if answer_el:
            inner = answer_el.find(class_="acordeon-header-respuesta")
            if inner:
                answer = _inline_to_md(inner)
            else:
                answer = _inline_to_md(answer_el)

        if question:
            sections.append(f"**{question}**")
            if answer:
                sections.append(f"{answer}\n")


# ─── Catalog overview page ─────────────────────────────────────────

def generate_catalog_overview() -> str:
    """Generate the main catalog overview markdown."""
    return """# Catálogo de Préstamos y Créditos BCP

**Haz realidad tus planes con nuestros créditos personales**

Pide tu préstamo BCP — Hazlo en segundos desde la web.

**Página del catálogo:** [Ver todos los créditos](https://www.viabcp.com/creditos)

---

## Categorías de Créditos

### Préstamos Personales (Crédito Efectivo)

Préstamos de dinero en efectivo para lo que necesites, con o sin garantía.

| Producto | Monto | Plazo | Garantía | Más detalles |
|----------|-------|-------|----------|-------------|
| Préstamo Personal | Hasta S/ 350,000 | 3 a 72 meses | Sin garantía | [Ver detalles](https://www.viabcp.com/creditos/credito-efectivo/prestamo-personal-bcp) |
| Préstamo con Garantía Hipotecaria | S/ 87,500 a S/ 600,000 | Hasta 15 años | Inmueble | [Ver detalles](https://www.viabcp.com/creditos/credito-efectivo/garantia-hipotecaria) |
| Préstamo Hipotecario Compartido | Desde S/ 87,500 | 1 a 10 años | Inmueble (2 propietarios) | [Ver detalles](https://www.viabcp.com/creditos/credito-efectivo/garantia-hipotecaria-compartida) |
| Préstamo con Garantía Líquida | Según depósito | 6 a 60 meses | Depósito a plazo | [Ver detalles](https://www.viabcp.com/creditos/credito-efectivo/garantia-liquida) |

### Créditos Hipotecarios

Financiamiento para la compra de vivienda, terreno o remodelación.

| Producto | Financiamiento | Plazo | Característica | Más detalles |
|----------|---------------|-------|----------------|-------------|
| Hipotecario Tradicional | Hasta 90% | 4 a 25 años | Prepagos gratis ilimitados | [Ver detalles](https://www.viabcp.com/creditos/credito-hipotecario/tradicional) |
| Hipotecario MiVivienda | Hasta S/ 355,100 | — | Bonos hasta S/ 5,400 | [Ver detalles](https://www.viabcp.com/creditos/credito-hipotecario/nuevo-credito-mivivienda) |
| Hipotecario Ahorro Local | — | — | Ahorro desde 4 meses como sustento | [Ver detalles](https://www.viabcp.com/creditos/credito-hipotecario/ahorro-local-fondeo-bcp) |
| Hipotecario MiVivienda Alquileres | — | — | Sustenta ingresos con alquiler | [Ver detalles](https://www.viabcp.com/creditos/credito-hipotecario/nuevo-credito-mivivienda/ahorro-local) |
| Hipotecario Compartido | 90% | — | Evalúa ingresos en conjunto | [Ver detalles](https://www.viabcp.com/creditos/credito-hipotecario/hipotecario-compartido) |
| Proyectos Inmobiliarios | — | — | Tasas y beneficios especiales | [Ver detalles](https://www.proyectosinmobiliariosbcp.com/) |

**Simulador Hipotecario:** [Simula tu crédito](https://www.viabcp.com/creditos/credito-hipotecario/simulador-credito-hipotecario)

### Créditos Vehiculares

Financiamiento para la compra de autos nuevos, seminuevos y usados.

| Producto | Plazo | Característica | Más detalles |
|----------|-------|----------------|-------------|
| Vehicular Inteligente | 24-36 meses | Menores costos de mantenimiento, renueva cada 2-3 años | [Ver detalles](https://www.viabcp.com/creditos/credito-vehicular/compra-inteligente) |
| Crédito Vehicular | Hasta 6 años | Desde S/ 15,000, autos nuevos/seminuevos/usados | [Ver detalles](https://www.viabcp.com/creditos/credito-vehicular/tradicional) |
| Crédito Auto Usado | Hasta 60 meses | Compra a personas naturales, sin seguro vehicular | [Ver detalles](https://www.viabcp.com/creditos/credito-vehicular/vehicular-autousado) |
| ExpoAutos | — | Elige, simula y solicita tu próximo auto | [Ver detalles](https://www.viabcp.com/expo-autos-bcp) |

**Simulador Vehicular:** [Simula tu crédito](https://www.viabcp.com/creditos/credito-vehicular/simulador-vehicular/)

### Otros Créditos

| Producto | Descripción | Más detalles |
|----------|-------------|-------------|
| Adelanto de Sueldo | Dinero extra de S/ 50 a S/ 2,500, comisión fija sin intereses, débito automático del próximo sueldo | [Ver detalles](https://www.viabcp.com/creditos/otros-creditos/adelanto-de-sueldo) |
| Yape Créditos | Préstamos desde S/ 50 hasta S/ 10,000 desde la app Yape, desembolso en minutos | [Ver detalles](https://www.viabcp.com/canales/yape/creditos-yape) |
| Cuotéalo sin Tarjeta | Compra en +1,000 marcas online sin tarjeta de crédito, desde TEA 8.9% | [Ver detalles](https://www.viabcp.com/cuotealo) |
| Préstamo Tarjetero | Accede hasta el 95% de tu línea de crédito a tasa preferencial | [Ver detalles](https://www.viabcp.com/creditos/otros-creditos/prestamo-tarjetero) |
| Préstamo Tarjetero Digital | Tu línea de crédito a la mano, plazos de 6 a 60 meses | [Ver detalles](https://www.viabcp.com/prestamo-tarjetero-digital) |
| Crédito Estudiantil | Financia maestrías, MBAs y doctorados, hasta S/ 300,000, plazos hasta 144 meses | [Ver detalles](https://www.viabcp.com/creditos/otros-creditos/credito-de-estudio) |

---

## ¿Cómo elegir tu crédito?

- **Necesitas dinero rápido sin garantía:** Préstamo Personal BCP (hasta S/ 350,000, TEA desde 8.9%)
- **Quieres comprar vivienda:** Crédito Hipotecario Tradicional (hasta 90% de financiamiento, hasta 25 años)
- **Quieres comprar tu primer hogar con apoyo estatal:** Crédito MiVivienda (bonos hasta S/ 5,400)
- **Quieres comprar un auto:** Crédito Vehicular (nuevos, seminuevos o usados, hasta 6 años)
- **Necesitas un adelanto pequeño hasta fin de mes:** Adelanto de Sueldo (S/ 50-2,500, comisión fija)
- **Quieres comprar online en cuotas sin tarjeta:** Cuotéalo (TEA desde 8.9%, +1,000 marcas)
- **Necesitas financiar estudios de posgrado:** Crédito Estudiantil (hasta S/ 300,000, hasta 144 meses)
- **Tienes línea de crédito y necesitas efectivo:** Préstamo Tarjetero (hasta 95% de tu línea)
"""


# ─── Main ──────────────────────────────────────────────────────────

def scrape_all_loans():
    """Main function: scrape all loan product pages."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("BCP Loans/Credits Scraper")
    print("=" * 60)

    # Generate catalog overview
    print("\n[1/3] Generating catalog overview...")
    overview_md = generate_catalog_overview()
    overview_path = os.path.join(OUTPUT_DIR, "catalogo-creditos-bcp.md")
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(overview_md)
    print(f"  -> Saved to {overview_path}")

    # Scrape catalog pages
    print("\n[2/3] Scraping catalog pages...\n")
    page_count = 0
    for product in LOAN_PRODUCTS:
        if not product["is_catalog"]:
            continue
        page_count += 1
        print(f"  [{page_count}] {product['name']} (catalog)")
        try:
            soup = fetch_page(product["url"])
            markdown = extract_catalog_page(soup, product)
            filepath = os.path.join(OUTPUT_DIR, f"{product['slug']}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"    -> Saved to {filepath}")
        except Exception as e:
            print(f"    ERROR: {e}")
        time.sleep(REQUEST_DELAY)

    # Scrape all detail pages (sub-products + standalone products)
    print("\n[3/3] Scraping detail pages...\n")
    all_detail_pages = []

    for product in LOAN_PRODUCTS:
        if product["is_catalog"]:
            for sub_name, sub_slug, sub_url in product["sub_products"]:
                all_detail_pages.append((sub_name, sub_slug, sub_url))
        else:
            all_detail_pages.append((
                product["name"], product["slug"], product["url"]
            ))

    total = len(all_detail_pages)
    for i, (name, slug, url) in enumerate(all_detail_pages, 1):
        print(f"  [{i}/{total}] {name}")
        try:
            soup = fetch_page(url)
            markdown = extract_detail_page(soup, name, url)
            filepath = os.path.join(OUTPUT_DIR, f"{slug}.md")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)
            print(f"    -> Saved to {filepath}")
        except Exception as e:
            print(f"    ERROR: {e}")

        if i < total:
            time.sleep(REQUEST_DELAY)

    print(f"\nDone! Files saved to {OUTPUT_DIR}/")


if __name__ == "__main__":
    scrape_all_loans()
