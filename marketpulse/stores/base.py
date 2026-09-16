import abc
import time
from typing import List, Optional
import httpx
from marketpulse.config import DEFAULT_HEADERS, REQUEST_TIMEOUT_SECONDS
from marketpulse.models import ProductResult, SearchCriteria


class BaseStoreProvider(abc.ABC):
    """
    Clase base para todos los conectores de tiendas.
    Garantiza una interfaz unificada y manejo robusto de peticiones y errores.
    """

    store_id: str = "base"
    store_name: str = "Base Store"
    base_url: str = ""

    def __init__(self, timeout: int = REQUEST_TIMEOUT_SECONDS):
        self.timeout = timeout
        self.client = httpx.Client(
            headers=DEFAULT_HEADERS.copy(),
            timeout=self.timeout,
            follow_redirects=True,
            http2=False
        )

    @abc.abstractmethod
    def build_search_url(self, criteria: SearchCriteria) -> str:
        """Construye la URL de búsqueda en la tienda con los parámetros aplicados."""
        pass

    @abc.abstractmethod
    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        """Ejecuta la búsqueda y devuelve la lista de productos encontrados."""
        pass

    def get_html(self, url: str) -> Optional[str]:
        """
        Realiza una petición GET segura con cabeceras realistas.
        Si la tienda responde con bloqueo WAF/antibot, captura la excepción amigablemente.
        """
        try:
            # Pausa de cortesía breve para evitar saturación
            time.sleep(0.3)
            response = self.client.get(url)
            if response.status_code == 200:
                return response.text
            elif response.status_code in [403, 503]:
                # Posible detección de bot por WAF de la tienda
                return None
            return None
        except Exception:
            return None

    def close(self):
        """Cierra la sesión HTTP."""
        try:
            self.client.close()
        except Exception:
            pass
