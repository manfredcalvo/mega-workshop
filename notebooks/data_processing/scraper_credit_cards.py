# Databricks notebook source
# COMMAND ----------
%pip install -r ../../requirements.txt
dbutils.library.restartPython()

# COMMAND ----------
"""
BCP Credit Card Web Scraper
Scrapes credit card details from viabcp.com and outputs markdown files
suitable for Databricks Knowledge Assistant ingestion.

Expects Databricks notebook widget parameters:
  - uc_catalog: Unity Catalog catalog name
  - uc_schema: Unity Catalog schema name
  - uc_volume: Unity Catalog volume name
Output is written to /Volumes/<catalog>/<schema>/<volume>/output_credit_cards/
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
CATALOG_URL = f"{BASE_URL}/tarjetas/tarjetas-credito"
OUTPUT_DIR = f"/Volumes/{uc_catalog}/{uc_schema}/{uc_volume}/output_credit_cards"
REQUEST_DELAY = 2  # seconds between requests

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-PE,es;q=0.9,en;q=0.8",
}

# Slugs to exclude from catalog scraping (not credit card detail pages)
EXCLUDED_SLUGS = {
    "debito", "comparador-de-tarjeta", "pago-sin-contacto",
    "tarjetas-credito", "tarjetas-credito-amex", "cargos-recurrentes",
}


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
            # Skip SVG containers and empty divs
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


def get_card_urls(soup: BeautifulSoup) -> list[dict]:
    """Extract card names and detail URLs from the catalog page."""
    cards = []
    seen_urls = set()

    for link in soup.find_all("a", href=True):
        href = link["href"]
        if not re.match(r"^/tarjetas/[a-z0-9-]+$", href):
            continue

        slug = href.split("/")[-1]
        if slug in EXCLUDED_SLUGS or href in seen_urls:
            continue
        seen_urls.add(href)

        # Find card name from parent product card element
        parent = link.find_parent(class_=re.compile(r"bcp-box-item|bcp-comp-producto"))
        name = ""
        if parent:
            title_el = parent.find(class_=re.compile(r"bcp-titulo"))
            if title_el:
                name = title_el.get_text(strip=True)

        if not name:
            name = link.get_text(strip=True) or slug

        cards.append({
            "name": name,
            "url": absolute_url(href),
            "slug": slug,
        })

    return cards


def extract_card_details(soup: BeautifulSoup, card_info: dict) -> str:
    """Extract all details from a card detail page and return markdown."""
    sections = []

    # 1. Card name and tagline from banner
    card_name = card_info["name"]
    tagline = ""

    banner = soup.find(class_="bcp-banner-interno")
    if not banner:
        banner = soup.find(class_=re.compile(r"bcp-banner-interno"))

    if banner:
        # .bcp-titulo has the real card name
        title_el = banner.find(class_="bcp-titulo")
        if title_el:
            card_name = title_el.get_text(strip=True)

        # .bcp-descripcion has the tagline
        desc_el = banner.find(class_="bcp-descripcion")
        if desc_el:
            tagline = desc_el.get_text(strip=True)

    # Also try h1 as fallback for card name
    if card_name == card_info["name"]:
        h1 = soup.find("h1")
        if h1:
            card_name = h1.get_text(strip=True)

    sections.append(f"# {card_name}\n")
    if tagline:
        sections.append(f"**{tagline}**\n")

    # Application link
    apply_link = None
    for a in soup.find_all("a", href=True):
        if "mitarjetabcp" in a.get("href", ""):
            apply_link = a["href"]
            break
    if apply_link:
        sections.append(f"**Solicítala aquí:** {apply_link}\n")

    sections.append("---\n")

    # 2. Benefit highlights (3-column grid)
    _extract_benefit_highlights(soup, sections)

    # 3. How to get it (tutorial carousel)
    _extract_tutorial_steps(soup, sections)

    # 4. Tabs section (Beneficios, Qore/LATAM, Tasas, Requisitos, etc.)
    _extract_tabs(soup, sections)

    # 5. FAQ section
    _extract_faq(soup, sections)

    return "\n".join(sections)


def _extract_benefit_highlights(soup: BeautifulSoup, sections: list):
    """Extract the 3-column benefit highlights section."""
    benefits_section = soup.find(class_="bcp_beneficio_presentacion_producto")
    if not benefits_section:
        return

    sections.append("## Beneficios Destacados\n")

    # Each benefit card is .bcp_beneficio_componente
    benefit_items = benefits_section.find_all(
        class_=re.compile(r"^bcp_beneficio_componente$")
    )
    if not benefit_items:
        # Try broader match
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

        key = (title, desc)
        if key in seen_benefits or not title:
            continue
        seen_benefits.add(key)

        if desc:
            sections.append(f"- **{title}:** {desc}")
        else:
            sections.append(f"- **{title}**")

    sections.append("\n---\n")


def _extract_tutorial_steps(soup: BeautifulSoup, sections: list):
    """Extract the 'how to get it' tutorial carousel steps."""
    tutorial = soup.find(class_="bcp_tutorial_tab_carousel")
    if not tutorial:
        return

    sections.append("## Cómo Obtenerla\n")

    # Steps are inside .swiper-wrapper > .swiper-slide.bcp_slide_item_tab
    # Find the swiper-wrapper that contains bcp_slide_item_tab slides
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

        # Deduplicate (responsive variants have same content)
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
    """Extract the tabbed content section (Beneficios, Tasas, Requisitos, etc.)."""
    tabs_container = soup.find(class_=re.compile(r"bcp_todo_lo_que_debes_saber"))
    if not tabs_container:
        return

    # Tab button labels
    tab_buttons = tabs_container.find_all(class_="bcp_tab_button")
    tab_names = [b.get_text(strip=True) for b in tab_buttons]

    # Tab content panels: .bcp_tab_componente_TIDS3.swiper-slide
    tab_panels = tabs_container.find_all(class_="bcp_tab_componente_TIDS3")

    for idx, panel in enumerate(tab_panels):
        tab_name = tab_names[idx] if idx < len(tab_names) else f"Sección {idx + 1}"

        # Extract rich text content from the panel
        content_text = extract_rich_text(panel)
        if not content_text.strip():
            continue

        sections.append(f"## {tab_name}\n")
        sections.append(content_text)

        # For Documentación tab, also extract doc links in a clean list
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

    # FAQ items are: .accordion-wrap > button.accordion-item (question) + .accordion-text (answer)
    accordion_wraps = faq_section.find_all(class_="accordion-wrap")
    if not accordion_wraps:
        return

    sections.append("## Preguntas Frecuentes\n")

    for wrap in accordion_wraps:
        # Question is in .accordion-header > h2
        header = wrap.find(class_="accordion-header")
        question = ""
        if header:
            h2 = header.find("h2")
            question = h2.get_text(strip=True) if h2 else header.get_text(strip=True)

        # Answer is in .accordion-text
        answer_el = wrap.find(class_="accordion-text")
        answer = ""
        if answer_el:
            # Get the inner content (usually in .acordeon-header-respuesta)
            inner = answer_el.find(class_="acordeon-header-respuesta")
            if inner:
                answer = _inline_to_md(inner)
            else:
                answer = _inline_to_md(answer_el)

        if question:
            sections.append(f"**{question}**")
            if answer:
                sections.append(f"{answer}\n")


def _extract_document_links(container) -> list[tuple[str, str]]:
    """Extract PDF/document download links from a container."""
    links = []
    seen = set()
    for a in container.find_all("a", href=True):
        href = a["href"]
        text = a.get_text(strip=True)
        if not text or not href:
            continue
        if ".pdf" in href.lower() or "/wcm/connect/" in href:
            full_url = absolute_url(href)
            if full_url not in seen:
                seen.add(full_url)
                links.append((text, full_url))
    return links


def extract_catalog_page(soup: BeautifulSoup) -> str:
    """Extract content from the credit card catalog page."""
    sections = []

    # Title and tagline from banner
    card_name = "Tarjetas de Crédito BCP"
    tagline = ""

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

    sections.append(f"**Página:** {CATALOG_URL}\n")
    sections.append("---\n")

    # Product boxes listing cards
    boxes = soup.find(class_=re.compile(
        r"bcp_boxes_tablero|bcp_listado_componente_boxes|bcp-box-item|bcp-comp-producto"
    ))
    if boxes:
        sections.append("## Tarjetas Disponibles\n")
        items = boxes.find_all(class_=re.compile(
            r"bcp_comp_box_tablero|bcp_contenedor_detalle_box|bcp-box-item"
        ))
        for item in items:
            title_el = item.find(class_=re.compile(r"bcp_titulo_box|bcp-titulo|titulo"))
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

    # Benefit highlights
    _extract_benefit_highlights(soup, sections)

    # Tabs section
    _extract_tabs(soup, sections)

    # FAQ
    _extract_faq(soup, sections)

    return "\n".join(sections)


def scrape_all_cards():
    """Main function: scrape catalog and all card detail pages."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print("=" * 60)
    print("BCP Credit Card Scraper")
    print("=" * 60)

    # Step 1: Fetch and save catalog overview
    print("\n[1/3] Fetching catalog page...")
    catalog_soup = fetch_page(CATALOG_URL)

    overview_md = extract_catalog_page(catalog_soup)
    overview_path = os.path.join(OUTPUT_DIR, "catalogo-tarjetas-credito-bcp.md")
    with open(overview_path, "w", encoding="utf-8") as f:
        f.write(overview_md)
    print(f"  -> Saved catalog overview to {overview_path}")

    # Step 2: Get all card URLs from catalog
    print("\n[2/3] Extracting card URLs...")
    cards = get_card_urls(catalog_soup)

    if not cards:
        print("WARNING: No cards found via scraping. Using hardcoded list.")
        cards = _hardcoded_cards()

    # Merge in any missing cards from hardcoded list
    scraped_slugs = {c["slug"] for c in cards}
    for hc in _hardcoded_cards():
        if hc["slug"] not in scraped_slugs:
            cards.append(hc)
            print(f"  Added missing card: {hc['name']}")

    print(f"  Found {len(cards)} credit cards\n")

    # Step 3: Scrape each card detail page
    print("[3/3] Scraping card detail pages...\n")
    for i, card in enumerate(cards, 1):
        print(f"  [{i}/{len(cards)}] {card['name']}")
        try:
            detail_soup = fetch_page(card["url"])
            markdown = extract_card_details(detail_soup, card)

            filename = f"{card['slug']}.md"
            filepath = os.path.join(OUTPUT_DIR, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(markdown)

            print(f"    -> Saved to {filepath}")

        except Exception as e:
            print(f"    ERROR: {e}")

        if i < len(cards):
            time.sleep(REQUEST_DELAY)

    print(f"\nDone! Files saved to {OUTPUT_DIR}/")


def _hardcoded_cards() -> list[dict]:
    """Fallback list of known card URLs."""
    slugs = [
        ("AMEX Clásica LATAM Pass", "american-express-clasica"),
        ("AMEX Oro LATAM Pass", "american-express-gold"),
        ("AMEX Platinum LATAM Pass", "american-express-platinum"),
        ("AMEX Black LATAM Pass", "american-express-black"),
        ("Visa Clásica LATAM Pass", "visa-latampass-clasica"),
        ("Visa Oro LATAM Pass", "visa-latampass-oro"),
        ("Visa Platinum LATAM Pass", "visa-latampass-platinum"),
        ("Visa Signature LATAM Pass", "visa-latampass-signature"),
        ("Visa Infinite Sapphire LATAM Pass", "sapphire"),
        ("Visa Infinite Iridium LATAM Pass", "visa-latampass-infinite"),
        ("Visa Clásica Qore", "visa-clasica-qore"),
        ("Visa Oro Qore", "visa-oro-qore"),
        ("Visa Platinum Qore", "visa-platinum-qore"),
        ("Visa Clásica", "credito-visa-clasica"),
        ("Visa Signature Qore", "visa-signature-qore"),
        ("Visa Infinite Qore", "visa-infinite-qore"),
        ("Visa Light", "credito-visa-light"),
        ("Visa iO", "credito-visa-io"),
    ]
    return [
        {"name": name, "slug": slug, "url": f"{BASE_URL}/tarjetas/{slug}"}
        for name, slug in slugs
    ]


if __name__ == "__main__":
    scrape_all_cards()
