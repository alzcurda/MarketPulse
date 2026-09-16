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
        html = self.get_html(search_url)
        results: List[ProductResult] = []

        if not html:
            return [
                ProductResult(
                    title=f"[Acceso directo] Catálogo Amazon España para: '{criteria.clean_query}'",
                    price=criteria.max_price or 0.0,
                    store_name=self.store_name,
                    url=search_url,
                    in_stock=True,
                    ships_from_spain=True,
                    match_score=85.0
                )
            ]

        soup = BeautifulSoup(html, "html.parser")
        items = soup.find_all("div", {"data-component-type": "s-search-result"})

        for item in items[:10]:
            title_node = item.find("h2")
            price_whole = item.find("span", class_="a-price-whole")
            price_fraction = item.find("span", class_="a-price-fraction")
            link_node = item.find("a", class_="a-link-normal s-no-outline") or (title_node.find("a") if title_node else None)

            if title_node and link_node:
                title = title_node.get_text(strip=True)
                price = 0.0
                if price_whole:
                    whole_str = price_whole.get_text(strip=True).replace(".", "").replace(",", "")
                    frac_str = price_fraction.get_text(strip=True) if price_fraction else "00"
                    try:
                        price = float(f"{whole_str}.{frac_str}")
                    except ValueError:
                        price = 0.0

                href = link_node.get("href") or ""
                if not href.startswith("http"):
                    href = urllib.parse.urljoin(self.base_url, href)

                # Limpiar parámetros de rastreo superfluos de la URL de Amazon
                clean_href = href.split("/ref=")[0] if "/ref=" in href else href

                results.append(
                    ProductResult(
                        title=title,
                        price=price,
                        store_name=self.store_name,
                        url=clean_href,
                        in_stock=True,
                        ships_from_spain=True
                    )
                )

        if not results:
            results.append(
                ProductResult(
                    title=f"Resultados Amazon.es para '{criteria.clean_query}'",
                    price=criteria.max_price or 0.0,
                    store_name=self.store_name,
                    url=search_url,
                    in_stock=True,
                    ships_from_spain=True,
                    match_score=80.0
                )
            )

        return results
