import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import httpx

from marketpulse import config
from marketpulse.models import ProductCategory, RefinementAspect

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Eres el Asesor Semántico de MarketPulse, un asistente experto de compras y catálogo multitienda.
Tu misión es analizar la petición de compra de un usuario para CUALQUIER producto comercial (informática, telefonía, herramientas, electrodomésticos, deporte, sonido, etc.).

Debes responder EXCLUSIVAMENTE con un objeto JSON válido con la siguiente estructura exacta:
{
  "product_type": "Nombre preciso de la tipología del artículo (ej: 'Mini PC', 'Cafetera superautomática', 'Taladro percutor a batería', 'Monitor gaming', 'Zapatillas running')",
  "category": "Una de las siguientes categorías exactas: 'portatiles', 'componentes_pc', 'smartphones', 'monitores', 'audio', 'gaming', 'electrodomesticos', 'tecnologia_general', 'otros'",
  "brand": "Marca detectada explícitamente en la consulta o null si no se mencionó",
  "model": "Modelo, serie o código específico detectado (ej: 'G10', 'Magnifica S', 'DCD796') o null",
  "clean_query": "Término de búsqueda optimizado para las tiendas (marca + modelo + producto sin palabras de relleno)",
  "is_generic": true si la búsqueda es amplia o tiene muchas configuraciones posibles sin detallar (ej: un mini pc sin RAM/disco, un taladro sin especificar batería/potencia, una cafetera sin tipo); false si el usuario ya fue muy específico,
  "min_price": número flotante si el usuario fijó presupuesto mínimo, o null,
  "max_price": número flotante si el usuario fijó presupuesto máximo, o null,
  "key_specs": ["lista", "de", "especificaciones", "ya", "mencionadas"],
  "refinement_aspects": [
    {
      "key": "identificador_corto (ej: ram, storage, milk_system, power_type, panel_type)",
      "question": "Pregunta concisa para orientar al comprador (ej: 'Memoria RAM deseada', 'Almacenamiento SSD', 'Sistema de leche')",
      "options": ["Opción 1", "Opción 2", "Opción 3", "Cualquiera / Indiferente"],
      "recommended_option": "Opción 1"
    }
  ]
}

REGLAS OBLIGATORIAS:
1. 'refinement_aspects' debe contener entre 2 y 4 aspectos técnicos que varíen sustancialmente el precio o la experiencia de ese producto. Si is_generic es false, puede ser una lista vacía.
2. Si el producto es un ordenador o Mini PC genérico, incluye preguntas sobre RAM (8GB, 16GB, 32GB), SSD (256GB, 512GB, 1TB) y si acepta Barebone.
3. No añadas texto explicativo ni bloques markdown fuera del JSON. Devuelve únicamente el JSON.
"""


class LLMClient:
    """
    Cliente universal para motores de lenguaje (LLM).
    Permite conectar con Ollama (local), Google Gemini (nube gratuita) o APIs compatibles OpenAI / LM Studio.
    """

    _cached_backend: Optional[str] = None
    _cached_backend_label: Optional[str] = None

    @classmethod
    def get_backend_info(cls) -> Tuple[str, str]:
        """
        Determina qué motor está activo y disponible.
        Devuelve (backend_id, label_legible).
        backend_id puede ser: "ollama", "gemini", "openai", "none".
        """
        if cls._cached_backend is not None and cls._cached_backend_label is not None:
            return cls._cached_backend, cls._cached_backend_label

        target = config.LLM_BACKEND

        # 1. Modo explícito: Ollama
        if target == "ollama":
            if cls._check_ollama():
                cls._cached_backend = "ollama"
                cls._cached_backend_label = f"Ollama Local ({config.OLLAMA_MODEL})"
                return cls._cached_backend, cls._cached_backend_label
            else:
                logger.warning(f"Ollama configurado en {config.OLLAMA_URL} pero no responde. Usando fallback.")
                cls._cached_backend = "none"
                cls._cached_backend_label = "Reglas Locales (Fallback - Ollama no activo)"
                return cls._cached_backend, cls._cached_backend_label

        # 2. Modo explícito: Gemini
        elif target == "gemini":
            if config.GEMINI_API_KEY:
                cls._cached_backend = "gemini"
                cls._cached_backend_label = f"Google Gemini ({config.GEMINI_MODEL})"
                return cls._cached_backend, cls._cached_backend_label
            else:
                logger.warning("Gemini configurado pero falta GEMINI_API_KEY.")
                cls._cached_backend = "none"
                cls._cached_backend_label = "Reglas Locales (Fallback - Sin GEMINI_API_KEY)"
                return cls._cached_backend, cls._cached_backend_label

        # 3. Modo explícito: OpenAI / Compatible
        elif target == "openai":
            if config.OPENAI_API_KEY or "localhost" in config.OPENAI_BASE_URL:
                cls._cached_backend = "openai"
                cls._cached_backend_label = f"OpenAI / Compatible ({config.OPENAI_MODEL})"
                return cls._cached_backend, cls._cached_backend_label
            else:
                cls._cached_backend = "none"
                cls._cached_backend_label = "Reglas Locales (Fallback)"
                return cls._cached_backend, cls._cached_backend_label

        # 4. Modo explícito: Ninguno
        elif target == "none":
            cls._cached_backend = "none"
            cls._cached_backend_label = "Reglas Locales (Sin IA)"
            return cls._cached_backend, cls._cached_backend_label

        # 5. Modo "auto" (Detección en cascada)
        # Paso 1: ¿Ollama activo en local?
        if cls._check_ollama():
            cls._cached_backend = "ollama"
            cls._cached_backend_label = f"Ollama Local ({config.OLLAMA_MODEL})"
            return cls._cached_backend, cls._cached_backend_label

        # Paso 2: ¿LM Studio activo en local?
        if cls._check_lm_studio():
            cls._cached_backend = "openai"
            cls._cached_backend_label = "LM Studio Local (OpenAI Compatible)"
            return cls._cached_backend, cls._cached_backend_label

        # Paso 3: ¿Gemini API Key configurada?
        if config.GEMINI_API_KEY:
            cls._cached_backend = "gemini"
            cls._cached_backend_label = f"Google Gemini ({config.GEMINI_MODEL})"
            return cls._cached_backend, cls._cached_backend_label

        # Paso 4: ¿OpenAI API Key configurada?
        if config.OPENAI_API_KEY:
            cls._cached_backend = "openai"
            cls._cached_backend_label = f"OpenAI ({config.OPENAI_MODEL})"
            return cls._cached_backend, cls._cached_backend_label

        # Paso 5: Fallback a reglas
        cls._cached_backend = "none"
        cls._cached_backend_label = "Reglas Locales Autónomas"
        return cls._cached_backend, cls._cached_backend_label

    @classmethod
    def _check_ollama(cls) -> bool:
        """Comprueba rápidamente si Ollama está en ejecución en el endpoint configurado."""
        try:
            r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    @classmethod
    def _check_lm_studio(cls) -> bool:
        """Comprueba rápidamente si LM Studio está activo en localhost:1234."""
        try:
            r = httpx.get("http://localhost:1234/v1/models", timeout=0.8)
            return r.status_code == 200
        except Exception:
            return False

    @classmethod
    def analyze_query(cls, raw_query: str) -> Optional[Dict[str, Any]]:
        """
        Envía la consulta del usuario al motor LLM activo y obtiene el análisis JSON estructurado.
        Si falla o no hay motor configurado, devuelve None.
        """
        backend, _ = cls.get_backend_info()
        if backend == "none":
            return None

        prompt = f"Analiza esta petición de compra de un usuario: '{raw_query}'"

        try:
            if backend == "ollama":
                return cls._call_ollama(prompt)
            elif backend == "gemini":
                return cls._call_gemini(prompt)
            elif backend == "openai":
                return cls._call_openai(prompt)
        except Exception as e:
            logger.debug(f"Error al consultar el backend LLM '{backend}': {e}")
            return None

        return None

    @classmethod
    def _clean_json_response(cls, text: str) -> Optional[Dict[str, Any]]:
        """Extrae y parsea de forma segura el bloque JSON devuelto por cualquier LLM."""
        if not text:
            return None
        text_clean = text.strip()
        # Eliminar bloques markdown ```json ... ```
        if text_clean.startswith("```"):
            text_clean = re.sub(r"^```(?:json)?\s*", "", text_clean)
            text_clean = re.sub(r"\s*```$", "", text_clean)
        text_clean = text_clean.strip()

        # Encontrar el primer '{' y el último '}'
        start_idx = text_clean.find("{")
        end_idx = text_clean.rfind("}")
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            json_str = text_clean[start_idx : end_idx + 1]
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
        try:
            return json.loads(text_clean)
        except Exception:
            return None

    @classmethod
    def _call_ollama(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Llamada a la API nativa de Ollama en local con salida JSON garantizada."""
        url = f"{config.OLLAMA_URL}/api/generate"
        payload = {
            "model": config.OLLAMA_MODEL,
            "system": SYSTEM_PROMPT,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1},
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                raw_response = data.get("response", "")
                return cls._clean_json_response(raw_response)
        return None

    @classmethod
    def _call_gemini(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Llamada directa y ligera a la API de Google Gemini en modo JSON."""
        api_key = config.GEMINI_API_KEY
        if not api_key:
            return None
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{config.GEMINI_MODEL}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"{SYSTEM_PROMPT}\n\n{prompt}"}],
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json",
            },
        }
        headers = {"Content-Type": "application/json"}
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        raw_text = parts[0].get("text", "")
                        return cls._clean_json_response(raw_text)
            else:
                logger.debug(f"Error Gemini API ({resp.status_code}): {resp.text}")
        return None

    @classmethod
    def _call_openai(cls, prompt: str) -> Optional[Dict[str, Any]]:
        """Llamada a endpoints compatibles con la API de OpenAI (OpenAI, LM Studio, Groq, etc.)."""
        base_url = config.OPENAI_BASE_URL.rstrip("/")
        url = f"{base_url}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if config.OPENAI_API_KEY:
            headers["Authorization"] = f"Bearer {config.OPENAI_API_KEY}"

        payload = {
            "model": config.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return cls._clean_json_response(content)
            else:
                logger.debug(f"Error OpenAI Compatible ({resp.status_code}): {resp.text}")
        return None
