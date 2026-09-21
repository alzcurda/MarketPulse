import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider
from marketpulse.core.pricing import parse_price


class WallapopProvider(BaseStoreProvider):
    """
    Conector para Wallapop con soporte para búsqueda de artículos de tecnología y electrónica
    de segunda mano con envío disponible a toda España (Wallapop Envíos).
    """

    store_id = "wallapop"
    store_name = "Wallapop (Segunda Mano)"
    base_url = "https://es.wallapop.com"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/app/search?keywords={query_encoded}"
        if criteria.min_price:
            url += f"&min_sale_price={int(criteria.min_price)}"
        if criteria.max_price:
            url += f"&max_sale_price={int(criteria.max_price)}"
        return url

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        queries = criteria.target_search_queries[:5] if criteria.target_search_queries else [criteria.clean_query]
        results: List[ProductResult] = []
        seen_items = set()

        for q in queries:
            query_encoded = urllib.parse.quote_plus(q)
            search_url = f"{self.base_url}/app/search?keywords={query_encoded}"

            query_max_price = criteria.max_price
            if criteria.max_price_by_cpu:
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.lower() in q.lower():
                        query_max_price = p_max
                        break

            if criteria.min_price:
                search_url += f"&min_sale_price={int(criteria.min_price)}"
            if query_max_price:
                search_url += f"&max_sale_price={int(query_max_price)}"

            html = self.get_browser_html(search_url, wait_timeout_ms=3000)
            if not html:
                continue

            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all("article")

            if not articles:
                item_links = soup.find_all("a", href=re.compile(r"/item/[a-z0-9-]+-\d+"))
                for link in item_links:
                    href = link.get("href", "")
                    m = re.search(r"/item/([a-z0-9-]+-(\d+))", href)
                    if not m:
                        continue
                    item_id = m.group(2)
                    if item_id in seen_items:
                        continue
                    seen_items.add(item_id)

                    full_url = f"{self.base_url}{href}" if href.startswith("/") else href
                    title = link.get("aria-label") or link.text.strip()
                    if not title or len(title) < 3:
                        continue

                    parent = link.parent
                    price_val = 0.0
                    for _ in range(3):
                        if parent:
                            price_el = parent.find(attrs={"aria-label": "Current price"}) or parent.find(class_=re.compile(r"currentPrice|price", re.I))
                            if price_el:
                                price_val = parse_price(price_el.text)
                                if price_val > 0:
                                    break
                            parent = parent.parent

                    results.append(
                        ProductResult(
                            title=title,
                            price=price_val,
                            store_name=self.store_name,
                            url=full_url,
                            in_stock=True,
                            ships_from_spain=True,
                        )
                    )
                continue

            for art in articles:
                a_link = art.find("a", href=re.compile(r"/item/"))
                if not a_link:
                    continue

                href = a_link.get("href", "")
                m = re.search(r"-(\d+)$", href)
                item_id = m.group(1) if m else href
                if item_id in seen_items:
                    continue
                seen_items.add(item_id)

                full_url = f"{self.base_url}{href}" if href.startswith("/") else href

                h3 = art.find("h3")
                title = h3.text.strip() if h3 else (a_link.get("aria-label") or a_link.text.strip())
                if not title:
                    continue

                price_el = art.find(attrs={"aria-label": "Current price"}) or art.find(class_=re.compile(r"currentPrice|price", re.I))
                price = parse_price(price_el.text) if price_el else 0.0

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
