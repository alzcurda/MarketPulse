import os
from typing import Dict

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
