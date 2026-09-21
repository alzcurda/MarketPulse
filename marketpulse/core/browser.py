import logging
from typing import Any, Optional, Tuple
from playwright.sync_api import Browser, BrowserContext, Playwright, sync_playwright

logger = logging.getLogger(__name__)


class BrowserSession:
    """
    Gestor singleton de sesión de navegador Playwright.
    Permite reutilizar una única instancia de navegador en segundo plano
    para realizar consultas rápidas bajo demanda evitando bloqueos por JS/WAF.
    """

    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _context: Optional[BrowserContext] = None

    @classmethod
    def get_context(cls) -> BrowserContext:
        if cls._context is None or cls._browser is None or not cls._browser.is_connected():
            if cls._playwright is None:
                cls._playwright = sync_playwright().start()

            launch_args = [
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars",
            ]

            try:
                # Intentar primero usar Google Chrome instalado en el sistema
                cls._browser = cls._playwright.chromium.launch(
                    channel="chrome",
                    headless=True,
                    args=launch_args,
                )
            except Exception:
                # Si no está disponible el canal chrome, usar el motor chromium por defecto
                cls._browser = cls._playwright.chromium.launch(
                    headless=True,
                    args=launch_args,
                )

            cls._context = cls._browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                viewport={"width": 1920, "height": 1080},
            )
            # Evadir comprobación básica de window.navigator.webdriver
            cls._context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        return cls._context

    @classmethod
    def fetch_page_data(
        cls,
        url: str,
        wait_timeout_ms: int = 2500,
        wait_until: str = "domcontentloaded",
        scroll_count: int = 0,
        scroll_delay_ms: int = 800,
        eval_js: Optional[str] = None,
    ) -> Tuple[Optional[str], Optional[any]]:
        """
        Navega a una URL con Playwright, opcionalmente realiza scroll y evalúa expresiones JS en la página.
        Devuelve una tupla (html_content, eval_result).
        """
        try:
            context = cls.get_context()
            page = context.new_page()
            try:
                page.goto(url, wait_until=wait_until, timeout=25000)
                if wait_timeout_ms > 0:
                    page.wait_for_timeout(wait_timeout_ms)

                if scroll_count > 0:
                    for _ in range(scroll_count):
                        page.mouse.wheel(0, 1500)
                        if scroll_delay_ms > 0:
                            page.wait_for_timeout(scroll_delay_ms)

                eval_result = None
                if eval_js:
                    try:
                        eval_result = page.evaluate(eval_js)
                    except Exception as e_eval:
                        logger.debug(f"Error evaluando JS en {url}: {e_eval}")

                html_content = page.content()
                return html_content, eval_result
            finally:
                page.close()
        except Exception as e:
            logger.debug(f"Error al navegar a {url}: {e}")
            return None, None

    @classmethod
    def fetch_html(
        cls,
        url: str,
        wait_timeout_ms: int = 2500,
        wait_until: str = "domcontentloaded",
        scroll_count: int = 0,
    ) -> Optional[str]:
        """
        Navega a una URL y obtiene el HTML procesado en el DOM tras la ejecución de JS.
        """
        html, _ = cls.fetch_page_data(
            url,
            wait_timeout_ms=wait_timeout_ms,
            wait_until=wait_until,
            scroll_count=scroll_count,
        )
        return html

    @classmethod
    def close(cls):
        """Cierra el contexto, navegador y sesión Playwright."""
        if cls._context:
            try:
                cls._context.close()
            except Exception:
                pass
            cls._context = None

        if cls._browser:
            try:
                cls._browser.close()
            except Exception:
                pass
            cls._browser = None

        if cls._playwright:
            try:
                cls._playwright.stop()
            except Exception:
                pass
            cls._playwright = None
