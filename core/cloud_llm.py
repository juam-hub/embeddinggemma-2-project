"""
Cloud LLM Provider Client for ChatCasero.
Supports OpenAI, Groq, Google Gemini (OpenAI compat), OpenRouter, and custom endpoints.
Handles streaming, multimodal base64 image encoding, connection testing, and secure key usage.
"""
import base64
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Generator, Tuple, Optional
import requests

CLOUD_PROVIDERS = {
    "groq": {
        "name": "Groq (Llama-3.3-70B · Ultra Rápido)",
        "base_url": "https://api.groq.com/openai/v1",
        "default_model": "llama-3.3-70b-versatile",
        "models": [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "llama-3.2-11b-vision-preview",
            "mixtral-8x7b-32768",
        ],
        "help": "Requiere API Key de console.groq.com (Gratuita y de altísima velocidad).",
    },
    "openai": {
        "name": "OpenAI (GPT-4o / GPT-4o-mini)",
        "base_url": "https://api.openai.com/v1",
        "default_model": "gpt-4o-mini",
        "models": [
            "gpt-4o-mini",
            "gpt-4o",
            "gpt-4-turbo",
            "gpt-3.5-turbo",
        ],
        "help": "Requiere API Key de platform.openai.com.",
    },
    "gemini": {
        "name": "Google Gemini (Gemini-1.5 / 2.0)",
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "default_model": "gemini-1.5-flash",
        "models": [
            "gemini-1.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
        ],
        "help": "Requiere API Key de aistudio.google.com.",
    },
    "openrouter": {
        "name": "OpenRouter (Claude, Llama, DeepSeek)",
        "base_url": "https://openrouter.ai/api/v1",
        "default_model": "meta-llama/llama-3.3-70b-instruct",
        "models": [
            "meta-llama/llama-3.3-70b-instruct",
            "deepseek/deepseek-chat",
            "anthropic/claude-3.5-sonnet",
            "mistralai/mistral-large-2407",
        ],
        "help": "Requiere API Key de openrouter.ai.",
    },
    "custom": {
        "name": "Personalizado (Compatible con OpenAI)",
        "base_url": "http://localhost:1234/v1",
        "default_model": "custom-model",
        "models": ["custom-model"],
        "help": "Permite conectar cualquier API compatible con OpenAI (vLLM, LM Studio, DeepSeek directo, proxies corporativos).",
    },
}


def get_provider_endpoint(provider: str, custom_url: Optional[str] = None) -> str:
    """Returns the chat completions URL for the given provider."""
    if provider == "custom" and custom_url:
        base = custom_url.strip().rstrip("/")
    else:
        info = CLOUD_PROVIDERS.get(provider, CLOUD_PROVIDERS["groq"])
        base = info["base_url"].rstrip("/")

    if not base.endswith("/chat/completions"):
        if base.endswith("/v1"):
            return f"{base}/chat/completions"
        elif base.endswith("/openai"):
            return f"{base}/chat/completions"
        else:
            return f"{base}/chat/completions"
    return base


def image_to_base64_data_uri(image_path: str) -> Optional[str]:
    """Encodes a local image file into a base64 Data URI."""
    p = Path(image_path)
    if not p.exists():
        return None
    try:
        suffix = p.suffix.lower()
        mime_type = "image/png"
        if suffix in [".jpg", ".jpeg"]:
            mime_type = "image/jpeg"
        elif suffix == ".webp":
            mime_type = "image/webp"

        with open(p, "rb") as f:
            encoded = base64.b64encode(f.read()).decode("utf-8")
        return f"data:{mime_type};base64,{encoded}"
    except Exception:
        return None


def format_messages_for_cloud(
    raw_messages: List[Dict[str, Any]],
    include_images: bool = True
) -> List[Dict[str, Any]]:
    """
    Converts internal messages list (which may contain 'images' in user turn)
    into standard OpenAI-compatible chat messages.
    """
    formatted = []
    for msg in raw_messages:
        role = msg.get("role", "user")
        content = msg.get("content", "")
        images = msg.get("images", [])

        if role == "user" and images and include_images:
            content_parts = [{"type": "text", "text": content}]
            for img_path in images:
                data_uri = image_to_base64_data_uri(img_path)
                if data_uri:
                    content_parts.append({
                        "type": "image_url",
                        "image_url": {"url": data_uri}
                    })
            formatted.append({"role": "user", "content": content_parts})
        else:
            formatted.append({"role": role, "content": content})

    return formatted


def test_cloud_connection(
    provider: str,
    api_key: str,
    model: str,
    custom_url: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validates API key and model availability with a minimal request.
    Returns (success: bool, status_message: str).
    """
    clean_key = (api_key or "").strip()
    if not clean_key:
        return False, "La clave de API está vacía. Por favor ingrésala para continuar."

    endpoint = get_provider_endpoint(provider, custom_url)
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://chatcasero.local"
        headers["X-Title"] = "ChatCasero"

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Hola"}
        ],
        "max_tokens": 5,
        "temperature": 0.1,
    }

    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=12)
        if response.status_code == 200:
            return True, f"¡Conexión exitosa con {model} ({provider})!"
        elif response.status_code == 401:
            return False, "Error 401: Clave de API no válida o expirada. Verifica tu clave."
        elif response.status_code == 404:
            return False, f"Error 404: El modelo '{model}' o el endpoint no fueron encontrados."
        elif response.status_code == 429:
            return False, "Error 429: Límite de cuota o tasa de peticiones excedido (Rate limit)."
        else:
            try:
                err_data = response.json()
                detail = err_data.get("error", {}).get("message", response.text[:200])
            except Exception:
                detail = response.text[:200]
            return False, f"Error {response.status_code}: {detail}"
    except requests.exceptions.Timeout:
        return False, "Tiempo de espera agotado (Timeout) al contactar la API en la nube."
    except requests.exceptions.ConnectionError:
        return False, f"No se pudo establecer conexión con el endpoint: {endpoint}"
    except Exception as e:
        return False, f"Error inesperado al conectar: {str(e)}"


def stream_cloud_chat(
    messages: List[Dict[str, Any]],
    provider: str,
    api_key: str,
    model: str,
    custom_url: Optional[str] = None,
    timeout: int = 60
) -> Generator[str, None, None]:
    """
    Sends streaming chat request to cloud provider.
    Yields text chunks as they arrive from the SSE stream.
    Safely falls back to text-only if multimodal image payload is rejected.
    """
    clean_key = (api_key or "").strip()
    if not clean_key:
        yield "⚠️ No se ha proporcionado una clave de API. Por favor, ingrésala en el panel lateral."
        return

    endpoint = get_provider_endpoint(provider, custom_url)
    headers = {
        "Authorization": f"Bearer {clean_key}",
        "Content-Type": "application/json",
    }
    if provider == "openrouter":
        headers["HTTP-Referer"] = "https://chatcasero.local"
        headers["X-Title"] = "ChatCasero"

    # Attempt with images first if present
    formatted_messages = format_messages_for_cloud(messages, include_images=True)
    payload = {
        "model": model,
        "messages": formatted_messages,
        "stream": True,
        "temperature": 0.2,
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            json=payload,
            stream=True,
            timeout=timeout
        )
    except Exception as e:
        yield f"*(Error de conexión con la nube: {str(e)})*"
        return

    # Check for HTTP errors
    if response.status_code != 200:
        error_text = ""
        try:
            err_json = response.json()
            error_text = err_json.get("error", {}).get("message", response.text)
        except Exception:
            error_text = response.text[:300]

        # If error was caused by images not supported by model, retry without images
        has_images = any(isinstance(m.get("content"), list) for m in formatted_messages)
        if has_images and (
            "image" in error_text.lower()
            or "vision" in error_text.lower()
            or "multimodal" in error_text.lower()
            or response.status_code == 400
        ):
            text_only_messages = format_messages_for_cloud(messages, include_images=False)
            payload["messages"] = text_only_messages
            try:
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    stream=True,
                    timeout=timeout
                )
            except Exception as e:
                yield f"*(Error en fallback textual de nube: {str(e)})*"
                return

        if response.status_code != 200:
            yield f"*(Error de API en la nube [{response.status_code}]: {error_text})*"
            return

    # Stream SSE response
    for line in response.iter_lines(decode_unicode=True):
        if not line:
            continue
        line_clean = line.strip()
        if line_clean.startswith("data: "):
            data_str = line_clean[6:].strip()
            if data_str == "[DONE]":
                break
            try:
                data = json.loads(data_str)
                choices = data.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {})
                    token = delta.get("content", "")
                    if token:
                        yield token
            except json.JSONDecodeError:
                continue
