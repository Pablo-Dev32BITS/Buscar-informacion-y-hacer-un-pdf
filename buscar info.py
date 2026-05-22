#By Pablito
#By Copilot

import requests
import wikipediaapi
from deep_translator import GoogleTranslator
from langdetect import detect, LangDetectException
from bs4 import BeautifulSoup
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from datetime import datetime
import textwrap
import re
import urllib.parse

# ---------- Config ----------
WIKIPEDIA_LANG = "es"
DUCKDUCKGO_SEARCH_URL = "https://html.duckduckgo.com/html/"
USER_AGENT = "BiografiaEspanol/1.0"

# ---------- Utilidades ----------
def safe_filename(name):
    return re.sub(r'[^A-Za-z0-9_-]', '_', name)

def traducir_a_es(text):
    if not text or text.strip() == "":
        return text
    try:
        # Detectar idioma; si ya es español, devolver original
        lang = detect(text)
        if lang == "es":
            return text
    except LangDetectException:
        pass
    try:
        return GoogleTranslator(source='auto', target='es').translate(text)
    except Exception:
        return text  # si falla la traducción, devolver original

# ---------- Wikipedia  ----------
def buscar_wikipedia_es(nombre):
    wiki = wikipediaapi.Wikipedia(language=WIKIPEDIA_LANG, user_agent=USER_AGENT)
    page = wiki.page(nombre)
    if page.exists():
        return {
            "title": page.title,
            "summary": page.summary,
            "text": page.text,
            "url": page.fullurl
        }
    return None

# ---------- Wikidata ----------
def buscar_wikidata_es(nombre):
    endpoint = "https://query.wikidata.org/sparql"
    q = """
    SELECT ?item ?itemLabel ?birthDate ?birthPlaceLabel ?deathDate ?residenceLabel WHERE {
      ?item rdfs:label "%s"@es.
      OPTIONAL { ?item wdt:P569 ?birthDate. }
      OPTIONAL { ?item wdt:P19 ?birthPlace. ?birthPlace rdfs:label ?birthPlaceLabel FILTER(LANG(?birthPlaceLabel) = "es") }
      OPTIONAL { ?item wdt:P570 ?deathDate. }
      OPTIONAL { ?item wdt:P551 ?residence. ?residence rdfs:label ?residenceLabel FILTER(LANG(?residenceLabel) = "es") }
      SERVICE wikibase:label { bd:serviceParam wikibase:language "es". }
    }
    LIMIT 1
    """ % nombre.replace('"', '\\"')
    headers = {"Accept": "application/sparql-results+json", "User-Agent": USER_AGENT}
    try:
        r = requests.get(endpoint, params={"query": q}, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data["results"]["bindings"]:
            b = data["results"]["bindings"][0]
            out = {}
            if "birthDate" in b: out["Fecha de nacimiento"] = b["birthDate"]["value"]
            if "birthPlaceLabel" in b: out["Lugar de nacimiento"] = b["birthPlaceLabel"]["value"]
            if "deathDate" in b: out["Fecha de fallecimiento"] = b["deathDate"]["value"]
            if "residenceLabel" in b: out["Residencia"] = b["residenceLabel"]["value"]
            if "item" in b: out["Wikidata"] = b["item"]["value"]
            return out
    except Exception:
        return None
    return None

# ---------- Búsqueda web y filtrado por idioma ----------
def buscar_web_duckduckgo_es(query, max_results=6):
    params = {"q": query}
    headers = {"User-Agent": "Mozilla/5.0 (compatible; %s)" % USER_AGENT}
    try:
        r = requests.post(DUCKDUCKGO_SEARCH_URL, data=params, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        results = []
        for res in soup.select("div.result")[:max_results]:
            a = res.select_one("a.result__a") or res.find("a", href=True)
            if not a:
                continue
            title = a.get_text(strip=True)
            href = a.get("href")
            parsed = urllib.parse.urlparse(href)
            if parsed.query:
                q = urllib.parse.parse_qs(parsed.query).get('uddg')
                if q:
                    href = q[0]
            snippet_tag = res.select_one(".result__snippet")
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""
            results.append({"title": title, "snippet": snippet, "url": href})
        return results
    except Exception:
        return []

# ---------- Extraer y asegurar texto en español ¡NO SACAR! ----------
def extraer_y_normalizar(url):
    headers = {"User-Agent": "Mozilla/5.0 (compatible; %s)" % USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=12)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # buscar primer párrafo significativo
        for p in soup.find_all("p"):
            text = p.get_text(strip=True)
            if len(text) > 60:
                texto = text
                texto_es = traducir_a_es(texto)
                return texto_es
    except Exception:
        return ""
    return ""

# ---------- Generar PDF en español con estilo moderno ----------
def crear_pdf_es(nombre_busqueda, titulo, datos_clave, secciones, referencias):
    filename = f"biografia_{safe_filename(nombre_busqueda)}.pdf"
    doc = SimpleDocTemplate(filename, pagesize=A4,
                            rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TitleCenter', parent=styles['Title'], alignment=TA_CENTER, fontSize=20, leading=24))
    styles.add(ParagraphStyle(name='Subtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=10, textColor=colors.grey))
    styles.add(ParagraphStyle(name='Heading', parent=styles['Heading2'], alignment=TA_LEFT, fontSize=14, textColor=colors.HexColor("#2E4057")))
    styles.add(ParagraphStyle(name='BodyJustify', parent=styles['BodyText'], alignment=TA_JUSTIFY, fontSize=10, leading=14))
    styles.add(ParagraphStyle(name='Key', parent=styles['Normal'], alignment=TA_LEFT, fontSize=10, leading=12, textColor=colors.HexColor("#1F618D")))

    flow = []
    # Portada
    flow.append(Spacer(1, 30))
    flow.append(Paragraph(f"Biografía: <b>{titulo}</b>", styles['TitleCenter']))
    flow.append(Spacer(1, 6))
    flow.append(Paragraph("Compilado automáticamente — verifica las fuentes para confirmar datos", styles['Subtitle']))
    flow.append(Spacer(1, 18))
    flow.append(Paragraph(f"Generado: {datetime.now().strftime('%Y-%m-%d %H:%M')}", styles['Subtitle']))
    flow.append(Spacer(1, 24))

    # Datos clave
    flow.append(Paragraph("Datos clave", styles['Heading']))
    flow.append(Spacer(1, 8))
    if datos_clave:
        table_data = []
        for k, v in datos_clave.items():
            table_data.append([Paragraph(f"<b>{k}</b>", styles['Key']), Paragraph(v, styles['BodyJustify'])])
        tbl = Table(table_data, colWidths=[130, 350], hAlign='LEFT')
        tbl.setStyle(TableStyle([
            ('BOX', (0,0), (-1,-1), 0.5, colors.grey),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.lightgrey),
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('LEFTPADDING', (0,0), (-1,-1), 6),
            ('RIGHTPADDING', (0,0), (-1,-1), 6),
        ]))
        flow.append(tbl)
    else:
        flow.append(Paragraph("No se encontraron datos estructurados.", styles['BodyJustify']))
    flow.append(Spacer(1, 18))

    # Secciones redactadas en español
    for sec_title, sec_text in secciones:
        flow.append(Paragraph(sec_title, styles['Heading']))
        flow.append(Spacer(1, 6))
        # dividir en párrafos manejables
        for paragraph in textwrap.wrap(sec_text, 500):
            flow.append(Paragraph(paragraph, styles['BodyJustify']))
            flow.append(Spacer(1, 6))
        flow.append(Spacer(1, 12))

    flow.append(PageBreak())

    # Fuentes
    flow.append(Paragraph("Fuentes y referencias", styles['Heading']))
    flow.append(Spacer(1, 8))
    for ref in referencias:
        flow.append(Paragraph(ref, styles['BodyJustify']))
        flow.append(Spacer(1, 6))

    doc.build(flow)
    return filename

# ---------- Flujo principal ----------
def main():
    nombre = input("Ingrese el nombre completo de la persona: ").strip()
    if not nombre:
        print("Nombre vacío. Saliendo.")
        return

    datos_clave = {}
    secciones = []
    referencias = []

    # 1) Wikipedia en español (prioritaria)
    print("Buscando en Wikipedia (es)...")
    wiki = buscar_wikipedia_es(nombre)
    if wiki:
        print("Página encontrada en Wikipedia (es).")
        resumen_es = traducir_a_es(wiki.get('summary', ''))  # normalmente ya es es, pero aseguramos
        texto_es = traducir_a_es(wiki.get('text', ''))
        secciones.append(("Resumen (Wikipedia)", resumen_es or ""))
        # intentar extraer datos clave del texto (patrones simples)
        m_birth = re.search(r'(?i)(naci[oó]n[:\s].{0,200})', texto_es)
        if m_birth:
            datos_clave["Nacimiento"] = m_birth.group(1)
        referencias.append(wiki.get('url'))
    else:
        print("No se encontró en Wikipedia en español.")

    # 2) Wikidata (etiquetas en español)
    print("Consultando Wikidata (etiquetas en español)...")
    wd = buscar_wikidata_es(nombre)
    if wd:
        print("Datos estructurados encontrados en Wikidata.")
        datos_clave.update(wd)
        if "Wikidata" in wd:
            referencias.append(wd["Wikidata"])
    else:
        print("No se encontraron datos en Wikidata en español.")

    # 3) Búsqueda web y extracción, priorizando contenido en español
    print("Buscando en la web (DuckDuckGo) y priorizando español...")
    web_results = buscar_web_duckduckgo_es(nombre, max_results=8)
    for r in web_results:
        url = r.get("url")
        title = r.get("title") or url
        snippet = r.get("snippet") or ""
        if not url:
            continue
        print(f"Procesando: {title} -> {url}")
        texto = extraer_y_normalizar(url)
        if not texto:
            # si no se pudo extraer, usar snippet y traducir si hace falta
            texto = traducir_a_es(snippet or title)
        secciones.append((f"Extracto: {title}", texto))
        referencias.append(url)

    if not secciones:
        secciones.append(("Resultados", "No se encontró información en las fuentes consultadas."))

    # 4) Generar PDF en español
    print("Generando PDF en español...")
    pdf_file = crear_pdf_es(nombre, nombre, datos_clave, secciones, referencias)
    print(f"PDF generado: {pdf_file}")

if __name__ == "__main__":
    main()
