import os
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from PIL import Image, ImageDraw, ImageFont
import pymupdf

from core.config import DATA_DIR
from core.stats_manager import StatsManager
from core.vector_store import VectorStore
from core.visual_analyzer import VisualAnalyzer
from core.pdf_extractor import PDFExtractor
from core.rag_engine import RAGEngine

def create_sample_pdf(pdf_path: Path):
    """Creates a sample PDF with text and an embedded statistical chart for testing."""
    doc = pymupdf.open()
    
    # Page 1: Pure text
    page1 = doc.new_page()
    page1.insert_text((50, 72), "INFORME TÉCNICO DE EFICIENCIA ENERGÉTICA 2026", fontsize=16)
    page1.insert_text(
        (50, 110),
        "Este documento presenta los resultados de rendimiento de sistemas fotovoltaicos y turbinas eólicas.\n"
        "Durante el primer trimestre se observó un incremento del 24% en la generación solar fotovoltaica,\n"
        "alcanzando una capacidad instalada neta de 450 Megavatios en la región norte.\n"
        "La estabilidad de la red eléctrica se mantuvo dentro de los parámetros nominales de 60 Hz.",
        fontsize=11
    )

    # Page 2: Text + Drawing (Vector elements)
    page2 = doc.new_page()
    page2.insert_text((50, 72), "PÁGINA 2: DISTRIBUCIÓN DE CONSUMO", fontsize=14)
    # Draw vector bars
    page2.draw_rect(pymupdf.Rect(60, 100, 100, 260), color=(0, 0, 1), fill=(0.2, 0.4, 0.8))
    page2.draw_rect(pymupdf.Rect(120, 140, 160, 260), color=(0, 0.8, 0), fill=(0.2, 0.8, 0.4))
    page2.draw_rect(pymupdf.Rect(180, 80, 220, 260), color=(1, 0, 0), fill=(0.9, 0.3, 0.3))
    page2.insert_text((60, 275), "Sector A", fontsize=10)
    page2.insert_text((120, 275), "Sector B", fontsize=10)
    page2.insert_text((180, 275), "Sector C", fontsize=10)

    # Page 3: Embedded Raster Image (Statistical Bar Chart with explicit labels)
    page3 = doc.new_page()
    page3.insert_text((50, 72), "PÁGINA 3: GRÁFICO COMPARATIVO ANUAL", fontsize=14)
    
    # Generate an image using PIL
    chart_img = Image.new("RGB", (400, 300), color=(255, 255, 255))
    draw = ImageDraw.Draw(chart_img)
    # Title
    draw.text((80, 15), "Generacion Solar vs Eolica (GWh)", fill=(0, 0, 0))
    # Axes
    draw.line([(50, 250), (370, 250)], fill=(0, 0, 0), width=2) # X
    draw.line([(50, 40), (50, 250)], fill=(0, 0, 0), width=2)   # Y
    # Bars
    draw.rectangle([(80, 120), (130, 250)], fill=(30, 144, 255))  # Solar 2025
    draw.rectangle([(150, 70), (200, 250)], fill=(0, 100, 200))   # Solar 2026: 180 GWh
    draw.rectangle([(230, 150), (280, 250)], fill=(46, 139, 87))  # Eolica 2025
    draw.rectangle([(300, 100), (350, 250)], fill=(34, 139, 34))  # Eolica 2026: 150 GWh
    # Labels
    draw.text((70, 260), "Solar 25", fill=(0, 0, 0))
    draw.text((140, 260), "Solar 26", fill=(0, 0, 0))
    draw.text((220, 260), "Eol 25", fill=(0, 0, 0))
    draw.text((290, 260), "Eol 26", fill=(0, 0, 0))
    draw.text((10, 60), "180", fill=(0, 0, 0))
    draw.text((10, 140), "100", fill=(0, 0, 0))
    
    temp_img_path = DATA_DIR / "temp_chart_test.png"
    chart_img.save(temp_img_path)

    # Insert image into page 3
    page3.insert_image(pymupdf.Rect(50, 100, 450, 400), filename=str(temp_img_path))

    doc.save(str(pdf_path))
    doc.close()
    if temp_img_path.exists():
        temp_img_path.unlink()
    print(f"Sample test PDF created at {pdf_path}")

def run_test():
    test_pdf = DATA_DIR / "test_document.pdf"
    create_sample_pdf(test_pdf)

    rag = RAGEngine()
    print("Testing document indexing...")
    stats = rag.index_document(test_pdf, progress_callback=lambda p, t: print(f"  [{int(p*100)}%] {t}"))

    print("\n--- STATS RESULT ---")
    print(f"Total pages: {stats['total_pages']}")
    print(f"Total visual elements: {stats['total_visual_elements']}")
    print(f"Total charts: {stats['total_charts']}")
    print(f"Total text chunks: {stats['total_text_chunks']}")
    print(f"Page map: {stats['page_map']}")

    print("\n--- SYSTEM PROMPT SHEET ---")
    print(rag.stats_manager.format_stats_sheet(test_pdf.name))

    print("\n--- QUERY TEST (Exact Counting) ---")
    stream, images = rag.query(test_pdf.name, "¿Cuántas imágenes y gráficos hay en total en el documento y en qué páginas?")
    answer = "".join(list(stream))
    print("Qwen Answer:\n", answer)
    print("Inspected images count:", len(images))

    print("\n--- QUERY TEST (Real-Time Visual Comprehension) ---")
    stream2, images2 = rag.query(test_pdf.name, "¿Qué valores muestra el gráfico de la página 3?")
    answer2 = "".join(list(stream2))
    print("Qwen Visual Answer:\n", answer2)
    print("Inspected images count:", len(images2))
    for im in images2:
        print("  - Inspected image:", im["id"], "Page:", im["page"], "Category:", im["category"])

if __name__ == "__main__":
    run_test()
