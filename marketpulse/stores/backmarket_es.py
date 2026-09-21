import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider
from marketpulse.core.pricing import parse_price


class BackMarketProvider(BaseStoreProvider):
    """
    Conector para Back Market España (backmarket.es).
    Líder europeo en tecnología y electrónica reacondicionada profesional,
    con 2 años de garantía oficial, 30 días de prueba y envío a domicilio a toda España.
    """

    store_id = "backmarket_es"
    store_name = "Back Market (Reacondicionado)"
    base_url = "https://www.backmarket.es"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/es-es/search?q={query_encoded}"
        if criteria.min_price:
            url += f"&min_price={int(criteria.min_price)}"
        if criteria.max_price:
            url += f"&max_price={int(criteria.max_price)}"
        return url

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        queries = criteria.target_search_queries[:4] if criteria.target_search_queries else [criteria.clean_query]
        results: List[ProductResult] = []
        seen_items = set()

        for q in queries:
            query_encoded = urllib.parse.quote_plus(q)
            search_url = f"{self.base_url}/es-es/search?q={query_encoded}"

            query_max_price = criteria.max_price
            if criteria.max_price_by_cpu:
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.lower() in q.lower():
                        query_max_price = p_max
                        break

            if criteria.min_price:
                search_url += f"&min_price={int(criteria.min_price)}"
            if query_max_price:
                search_url += f"&max_price={int(query_max_price)}"

            html = self.get_browser_html(search_url, wait_timeout_ms=4000)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            price_boxes = soup.find_all("div", attrs={"data-qa": "productCardPrice"})

            for p_box in price_boxes:
                # Localizar el contenedor o enlace al producto
                ancestor = p_box
                a_link = None
                for _ in range(8):
                    if ancestor:
                        a_link = ancestor.find("a", href=re.compile(r"/es-es/p/"))
                        if a_link:
                            break
                        ancestor = ancestor.parent

                if not a_link:
                    continue

                href = a_link.get("href", "")
                m = re.search(r"/p/([^/?]+)", href)
                item_id = m.group(1) if m else href
                if item_id in seen_items:
                    continue
                seen_items.add(item_id)

                full_url = f"{self.base_url}{href}" if href.startswith("/") else href

                # Extraer título limpio
                title_span = a_link.find("span", class_=re.compile(r"body-1-bold|line-clamp"))
                title = title_span.text.strip() if title_span else a_link.text.strip()
                if not title or len(title) < 3:
                    continue

                # Extraer precio reacondicionado (evitando el precio nuevo tachado)
                h2 = p_box.find("span", class_=re.compile(r"heading-2"))
                price_text = h2.text.strip().replace("\n", "") if h2 else p_box.text
                price = parse_price(price_text)

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
