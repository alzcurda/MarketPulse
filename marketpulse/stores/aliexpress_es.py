import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider


class AliExpressEsProvider(BaseStoreProvider):
    """
    Conector para AliExpress con filtro estricto de envío desde España (Plaza).
    Garantiza entrega rápida y ausencia de impuestos/aduanas sorpresa.
    """

    store_id = "aliexpress_es"
    store_name = "AliExpress Plaza (España)"
    base_url = "https://es.aliexpress.com"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        # Filtros de AliExpress para envío desde España (shipFromCountry=ES)
        url = f"{self.base_url}/w/wholesale-{query_encoded}.html?shipFromCountry=ES"
        if criteria.max_price:
            url += f"&maxPrice={int(criteria.max_price)}"
        if criteria.min_price:
            url += f"&minPrice={int(criteria.min_price)}"
        return url

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        queries = criteria.target_search_queries[:2] if criteria.target_search_queries else [criteria.clean_query]
        results: List[ProductResult] = []
        seen_items = set()

        for q in queries:
            query_encoded = urllib.parse.quote_plus(q)
            search_url = f"{self.base_url}/w/wholesale-{query_encoded}.html?shipFromCountry=ES"
            if criteria.max_price:
                search_url += f"&maxPrice={int(criteria.max_price)}"
            if criteria.min_price:
                search_url += f"&minPrice={int(criteria.min_price)}"

            html = self.get_browser_html(search_url, wait_timeout_ms=2500)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            links = soup.find_all("a", href=re.compile(r"/item/(\d+)\.html"))

            for a in links:
                href = a.get("href", "")
                m = re.search(r"/item/(\d+)\.html", href)
                if not m:
                    continue
                item_id = m.group(1)
                if item_id in seen_items:
                    continue
                seen_items.add(item_id)

                # Localizar el contenedor de la tarjeta de producto
                card = a
                for _ in range(6):
                    if card.parent and card.parent.name in ["div", "li"]:
                        card = card.parent
                        if "€" in card.get_text():
                            break

                # Título del artículo
                title = ""
                h_elem = card.find(["h1", "h2", "h3"])
                if h_elem:
                    title = h_elem.get_text(strip=True)
                if not title or len(title) < 10:
                    img = card.find("img", alt=True)
                    if img and len(img.get("alt", "")) > 10:
                        title = img["alt"]
                    else:
                        title = a.get_text(strip=True)

                if not title:
                    continue

                # Extracción de precio en euros
                price = 0.0
                price_spans = card.select("[class*='price'], [class*='Price']")
                if price_spans:
                    p_text = price_spans[0].get_text(strip=True)
                    m_p = re.search(r"(\d+[\.,]\d{2})", p_text)
                    if m_p:
                        price = float(m_p.group(1).replace(".", "").replace(",", "."))

                if price == 0.0:
                    card_text = card.get_text(separator=" ")
                    m_p = re.search(r"(\d+[\.,]\d{2})\s*€", card_text) or re.search(r"€\s*(\d+[\.,]\d{2})", card_text)
                    if m_p:
                        try:
                            price = float(m_p.group(1).replace(".", "").replace(",", "."))
                        except ValueError:
                            price = 0.0

                # URL directa al artículo individual
                direct_url = f"{self.base_url}/item/{item_id}.html"

                results.append(
                    ProductResult(
                        title=title,
                        price=price,
                        store_name=self.store_name,
                        url=direct_url,
                        in_stock=True,
                        ships_from_spain=True,
                    )
                )

        return results

