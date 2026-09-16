import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider


class AmazonEsProvider(BaseStoreProvider):
    """Conector para Amazon España (Amazon.es)."""

    store_id = "amazon_es"
    store_name = "Amazon España"
    base_url = "https://www.amazon.es"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/s?k={query_encoded}"
        if criteria.max_price:
            # Amazon usa filtros de precio en céntimos o rango
            url += f"&rh=p_36%3A-{int(criteria.max_price * 100)}"
        return url

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        search_url = self.build_search_url(criteria)
        # Intentar obtener el HTML renderizado por navegador para evitar el bloqueo Akamai WAF
        html = self.get_browser_html(search_url, wait_timeout_ms=1800)
        if not html:
            html = self.get_html(search_url)

        results: List[ProductResult] = []
        if not html:
            return []

        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", {"data-component-type": "s-search-result"})

        for item in items:
            asin = item.get("data-asin")
            if not asin:
                continue

            title_node = item.find("h2")
            if not title_node:
                continue

            title = title_node.get_text(strip=True)
            if not title:
                continue

            # Enlace directo al artículo individual mediante su ASIN oficial
            direct_url = f"{self.base_url}/dp/{asin}"

            # Extracción de precio
            price = 0.0
            price_offscreen = item.select_one(".a-price .a-offscreen")
            raw_price = price_offscreen.get_text(strip=True) if price_offscreen else ""

            if not raw_price:
                # Buscar patrón de precio en los elementos de texto de la tarjeta
                for s in item.stripped_strings:
                    if "€" in s or "eur" in s.lower():
                        raw_price = s
                        break

            price_match = re.search(r"(\d+[\.,]\d{2})", raw_price)
            if price_match:
                try:
                    price = float(price_match.group(1).replace(".", "").replace(",", "."))
                except ValueError:
                    price = 0.0

            # Porcentaje de descuento si existe oferta
            discount = None
            discount_badge = item.select_one(".savingsPercentage, [class*='savingsPercentage']")
            if discount_badge:
                m_d = re.search(r"(\d+)%", discount_badge.get_text())
                if m_d:
                    discount = float(m_d.group(1))

            results.append(
                ProductResult(
                    title=title,
                    price=price,
                    store_name=self.store_name,
                    url=direct_url,
                    in_stock=True,
                    ships_from_spain=True,
                    discount_percentage=discount
                )
            )

        return results
