import os
from typing import Dict
from dotenv import load_dotenv

# Cargar variables desde archivo .env local si existe
load_dotenv()

# Configuración general
APP_NAME = "MarketPulse"
DEFAULT_COUNTRY = "ES"
DEFAULT_CURRENCY = "EUR"
REQUEST_TIMEOUT_SECONDS = 15

# Cabeceras estándar para simular navegación de escritorio ética y evitar bloqueos por cabeceras vacías
DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
}

# Tiendas activadas por defecto
AVAILABLE_STORES = [
    "pccomponentes",
    "amazon_es",
    "mediamarkt",
    "aliexpress_es",
]

# Configuración del Motor de Inteligencia Semántica / LLM
# Valores posibles para LLM_BACKEND: "auto", "ollama", "gemini", "openai", "none"
LLM_BACKEND = os.getenv("LLM_BACKEND", "auto").lower()

# 1. Parámetros Ollama (Instancia Local)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")

# 2. Parámetros Google Gemini (Nube / Gratis en Google AI Studio)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# 3. Parámetros OpenAI / LM Studio / Compatible
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
