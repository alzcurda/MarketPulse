import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider
from marketpulse.core.pricing import parse_price


class CexProvider(BaseStoreProvider):
    """
    Conector para CeX España (es.webuy.com).
    Especialista en compra y venta de tecnología y electrónica de segunda mano testada,
    con garantía oficial de 5 años y envío a toda España.
    """

    store_id = "cex_es"
    store_name = "CeX Webuy (Segunda Mano)"
    base_url = "https://es.webuy.com"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        return f"{self.base_url}/search?stext={query_encoded}"

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        queries = criteria.target_search_queries[:4] if criteria.target_search_queries else [criteria.clean_query]
        results: List[ProductResult] = []
        seen_items = set()

        for q in queries:
            query_encoded = urllib.parse.quote_plus(q)
            search_url = f"{self.base_url}/search?stext={query_encoded}"

            html = self.get_browser_html(search_url, wait_timeout_ms=3500)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            cards = soup.find_all("div", class_=re.compile(r"cx-card-product"))

            for card in cards:
                title_box = card.find(class_=re.compile(r"card-title"))
                a_link = title_box.find("a") if title_box else card.find("a", href=re.compile(r"/product-detail\?id="))
                if not a_link:
                    continue

                href = a_link.get("href", "")
                m = re.search(r"id=([^&]+)", href)
                item_id = m.group(1) if m else href
                if item_id in seen_items:
                    continue
                seen_items.add(item_id)

                full_url = f"{self.base_url}{href}" if href.startswith("/") else href
                title = a_link.get("title") or a_link.text.strip()
                if not title:
                    continue

                price_el = card.find(class_=re.compile(r"product-main-price")) or card.find(class_=re.compile(r"price-wrapper"))
                price = parse_price(price_el.text) if price_el else 0.0

                # Comprobación de presupuesto
                if criteria.max_price and price > criteria.max_price:
                    continue
                if criteria.min_price and price < criteria.min_price:
                    continue

                results.append(
                    ProductResult(
                        title=title,
                        price=price,
                        store_name=self.store_name,
                        url=full_url,
                        in_stock=True,
                        ships_from_spain=True,
                    )
                )

        return results
