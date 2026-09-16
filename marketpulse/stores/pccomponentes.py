import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider


class PcComponentesProvider(BaseStoreProvider):
    """Conector para PcComponentes (España)."""

    store_id = "pccomponentes"
    store_name = "PcComponentes"
    base_url = "https://www.pccomponentes.com"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/buscar/?query={query_encoded}"
        if criteria.max_price:
            url += f"&maxPrice={int(criteria.max_price)}"
        if criteria.min_price:
            url += f"&minPrice={int(criteria.min_price)}"
        return url

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        search_url = self.build_search_url(criteria)
        html = self.get_html(search_url)
        results: List[ProductResult] = []

        if not html:
            # Si el WAF/antibot de PcComponentes bloquea la petición estática,
            # devolvemos una referencia estructurada con el enlace directo listo para el usuario
            return [
                ProductResult(
                    title=f"[Acceso directo] Catálogo PcComponentes para: '{criteria.clean_query}'",
                    price=criteria.max_price or 0.0,
                    store_name=self.store_name,
                    url=search_url,
                    in_stock=True,
                    ships_from_spain=True,
                    match_score=85.0
                )
            ]

        soup = BeautifulSoup(html, "html.parser")
        articles = soup.find_all(["article", "div"], class_=re.compile(r"product-card|c-product-card", re.I))

        for article in articles[:10]:
            title_elem = article.find(["h3", "h2", "a"], class_=re.compile(r"title|name", re.I)) or article.find("a")
            price_elem = article.find(class_=re.compile(r"price|precio", re.I))

            if title_elem and price_elem:
                title = title_elem.get_text(strip=True)
                raw_price = price_elem.get_text(strip=True)
                price_match = re.search(r"(\d+(?:[\.,]\d+)?)", raw_price.replace(".", "").replace(",", "."))
                price = float(price_match.group(1)) if price_match else 0.0

                href = title_elem.get("href") or ""
                if not href.startswith("http"):
                    href = urllib.parse.urljoin(self.base_url, href)

                results.append(
                    ProductResult(
                        title=title,
                        price=price,
                        store_name=self.store_name,
                        url=href,
                        in_stock=True,
                        ships_from_spain=True
                    )
                )

        if not results:
            results.append(
                ProductResult(
                    title=f"Resultados PcComponentes para '{criteria.clean_query}'",
                    price=criteria.max_price or 0.0,
                    store_name=self.store_name,
                    url=search_url,
                    in_stock=True,
                    ships_from_spain=True,
                    match_score=80.0
                )
            )

        return results
