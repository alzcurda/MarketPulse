import re
import urllib.parse
from typing import List
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider


class MediaMarktProvider(BaseStoreProvider):
    """Conector para MediaMarkt España."""

    store_id = "mediamarkt"
    store_name = "MediaMarkt"
    base_url = "https://www.mediamarkt.es"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/es/search.html?query={query_encoded}"
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
            # Enlaces a productos en MediaMarkt contienen /es/product/
            product_links = soup.find_all("a", href=re.compile(r"/es/product/"))
            seen_urls = set()

            for a_tag in product_links:
                href = a_tag.get("href", "")
                if not href.startswith("http"):
                    href = urllib.parse.urljoin(self.base_url, href)

                clean_url = href.split("?")[0]
                if clean_url in seen_urls:
                    continue
                seen_urls.add(clean_url)

                title = a_tag.get_text(strip=True)
                if not title or len(title) < 10:
                    continue

                card = a_tag
                for _ in range(5):
                    if card.parent and card.parent.name in ["div", "li"]:
                        card = card.parent
                        if "€" in card.get_text():
                            break

                price = 0.0
                card_text = card.get_text(separator=" ")
                m_p = re.search(r"(\d+[\.,]\d{2})\s*€", card_text) or re.search(r"€\s*(\d+[\.,]\d{2})", card_text)
                if m_p:
                    try:
                        price = float(m_p.group(1).replace(".", "").replace(",", "."))
                    except ValueError:
                        price = 0.0

                results.append(
                    ProductResult(
                        title=title,
                        price=price,
                        store_name=self.store_name,
                        url=clean_url,
                        in_stock=True,
                        ships_from_spain=True
                    )
                )

        # 2. Si el WAF/Akamai bloqueó el acceso directo, indexar artículos de MediaMarkt
        if not results:
            try:
                import httpx
                resp = httpx.post(
                    "https://lite.duckduckgo.com/lite/",
                    data={"q": f"site:mediamarkt.es/es/product/ {criteria.clean_query}"},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                    timeout=8.0
                )
                if resp.status_code == 200:
                    soup_idx = BeautifulSoup(resp.text, "html.parser")
                    links = soup_idx.find_all("a", class_="result-link")
                    snippets = soup_idx.find_all("td", class_="result-snippet")
                    seen_urls = set()
                    for i, a_elem in enumerate(links):
                        href = a_elem.get("href", "")
                        if "/es/product/" in href and href not in seen_urls:
                            seen_urls.add(href)
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

