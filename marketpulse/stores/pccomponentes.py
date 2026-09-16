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
        results: List[ProductResult] = []

        # 1. Intentar renderizar la página oficial con Playwright
        html = self.get_browser_html(search_url, wait_timeout_ms=2500)
        if not html:
            html = self.get_html(search_url)

        if html and "momento" not in html.lower():
            soup = BeautifulSoup(html, "html.parser")
            articles = soup.find_all(["article", "div"], class_=re.compile(r"product-card|c-product-card", re.I))

            for article in articles:
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

                    if "/buscar" not in href and title:
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

        # 2. Si el WAF/Cloudflare bloqueó el acceso directo, indexar artículos reales de PcComponentes
        if not results:
            try:
                import httpx
                resp = httpx.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": f"site:pccomponentes.com {criteria.clean_query}"},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=8.0
                )
                if resp.status_code == 200:
                    soup_idx = BeautifulSoup(resp.text, "html.parser")
                    links = soup_idx.find_all("a", class_="result-link")
                    snippets = soup_idx.find_all("td", class_="result-snippet")
                    for i, a_elem in enumerate(links):
                        href = a_elem.get("href", "")
                        if "pccomponentes.com/" in href and not any(x in href for x in ["/buscar", "/soporte", "/login", "/cart", "/opiniones"]):
                            title = a_elem.get_text(strip=True)
                            snippet = snippets[i].get_text(strip=True) if i < len(snippets) else ""
                            m_p = re.search(r"(\d+[\.,]\d{2})\s*€", snippet)
                            price = float(m_p.group(1).replace(".", "").replace(",", ".")) if m_p else 0.0
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
            except Exception:
                pass

        return results
