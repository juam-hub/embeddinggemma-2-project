import json
import re
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image
import ollama
from core.config import VISION_MODEL, VISION_OPTIONS

CATEGORIES = [
    "Gráfico estadístico",
    "Diagrama",
    "Tabla visual",
    "Fotografía/Ilustración"
]

def prepare_image_for_model(image_path: Path, max_dim: int = 768) -> str:
    """Downscales large images to max_dim to optimize VRAM and vision token consumption."""
    try:
        with Image.open(image_path) as img:
            if img.width > max_dim or img.height > max_dim:
                img_copy = img.copy()
                img_copy.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
                temp_opt = image_path.parent / f"_opt_{image_path.name}"
                img_copy.save(temp_opt, format="PNG", optimize=True)
                return str(temp_opt)
    except Exception:
        pass
    return str(image_path)

ANALYSIS_PROMPT = """Analiza minuciosamente esta imagen o gráfico extraído de un documento técnico/académico.
Debes responder ÚNICAMENTE con un objeto JSON válido con la siguiente estructura:
{
  "categoria": "Una de estas opciones exactas: 'Gráfico estadístico', 'Diagrama', 'Tabla visual', 'Fotografía/Ilustración'",
  "transcripcion": "Transcripción textual exhaustiva de todo lo que esté escrito en la imagen: títulos, subtítulos, etiquetas de ejes X e Y, leyendas, unidades de medida, números, datos tabulares y anotaciones.",
  "descripcion_detallada": "Descripción semántica y analítica completa de lo que representa el elemento, tendencias observadas, conclusiones o relaciones mostradas."
}

Reglas estrictas:
1. 'categoria' DEBE ser exactamente una de:
   - 'Gráfico estadístico' (barras, líneas, curvas, torta, dispersión, histogramas)
   - 'Diagrama' (flujogramas, arquitectura, esquemas conceptuales, mapas de procesos)
   - 'Tabla visual' (matrices o tablas de datos numéricos/textuales)
   - 'Fotografía/Ilustración' (fotografías reales, imágenes microscópicas, personas, objetos, capturas)
2. Transcribe todos los textos y cifras legibles con la máxima fidelidad.
3. Responde únicamente con el JSON sin bloques de código markdown ni texto adicional.
"""

class VisualAnalyzer:
    def __init__(self, model: str = VISION_MODEL, options: dict = VISION_OPTIONS):
        self.model = model
        self.options = options
        self.client = ollama.Client()

    def analyze_image(self, image_path: Path) -> Dict[str, Any]:
        """
        Sends the image to qwen2.5vl:7b with options={"num_ctx": 8192} (GPU).
        Returns structured analysis with category, transcription, and detailed description.
        """
        image_path = Path(image_path)
        if not image_path.exists():
            return {
                "categoria": "Fotografía/Ilustración",
                "transcripcion": "",
                "descripcion_detallada": "Archivo de imagen no encontrado."
            }

        # Optimize image dimension for fast inference and reduced tokens
        model_image_path = prepare_image_for_model(image_path, max_dim=768)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": ANALYSIS_PROMPT,
                        "images": [model_image_path]
                    }
                ],
                options=self.options
            )

            raw_content = response.message.content.strip()

            # Clean JSON if wrapped in markdown code blocks
            clean_json = raw_content
            if "```" in clean_json:
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json)
                clean_json = re.sub(r"\s*```$", "", clean_json)
            clean_json = clean_json.strip()

            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError:
                # Attempt to extract first { ... } block
                match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                if match:
                    data = json.loads(match.group(0))
                else:
                    data = {
                        "categoria": "Fotografía/Ilustración",
                        "transcripcion": "",
                        "descripcion_detallada": raw_content
                    }

            # Normalize category
            cat = data.get("categoria", "").strip()
            matched_cat = "Fotografía/Ilustración"
            for c in CATEGORIES:
                if c.lower() in cat.lower() or cat.lower() in c.lower():
                    matched_cat = c
                    break

            transcription = data.get("transcripcion", "").strip()
            description = data.get("descripcion_detallada", "").strip() or raw_content

            return {
                "categoria": matched_cat,
                "transcripcion": transcription,
                "descripcion_detallada": description
            }

        except Exception as e:
            return {
                "categoria": "Fotografía/Ilustración",
                "transcripcion": "",
                "descripcion_detallada": f"Error en análisis visual: {str(e)}"
            }
