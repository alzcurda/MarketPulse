import abc
import time
from typing import Any, List, Optional, Tuple
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

    def get_browser_html(self, url: str, wait_timeout_ms: int = 2500, wait_until: str = "domcontentloaded", scroll_count: int = 0) -> Optional[str]:
        """
        Obtiene el HTML renderizado mediante navegador headless Playwright.
        Indispensable para tiendas con protección antibot o contenido generado por cliente JS.
        """
        from marketpulse.core.browser import BrowserSession
        return BrowserSession.fetch_html(url, wait_timeout_ms=wait_timeout_ms, wait_until=wait_until, scroll_count=scroll_count)

    def get_browser_page_data(
        self,
        url: str,
        wait_timeout_ms: int = 2500,
        wait_until: str = "domcontentloaded",
        scroll_count: int = 0,
        eval_js: Optional[str] = None
    ) -> Tuple[Optional[str], Optional[Any]]:
        """
        Obtiene el HTML renderizado y el resultado de evaluar JS mediante navegador headless Playwright.
        """
        from marketpulse.core.browser import BrowserSession
        return BrowserSession.fetch_page_data(
            url,
            wait_timeout_ms=wait_timeout_ms,
            wait_until=wait_until,
            scroll_count=scroll_count,
            eval_js=eval_js
        )

    def close(self):
        """Cierra la sesión HTTP."""
        try:
            self.client.close()
        except Exception:
            pass
