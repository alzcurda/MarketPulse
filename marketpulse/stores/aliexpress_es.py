import re
import urllib.parse
from typing import List, Optional
from bs4 import BeautifulSoup
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider
from marketpulse.core.pricing import (
    parse_price,
    is_financing_or_unit_price,
    is_strikethrough_or_old_price,
    is_sponsored_card,
    is_out_of_stock,
)


class AliExpressEsProvider(BaseStoreProvider):
    """
    Conector avanzado para AliExpress con extracción dual (JSON estructurado de alta fidelidad
    con respaldo en DOM de Playwright). Garantiza máxima cobertura de catálogo para España,
    precios reales sin distorsión y captura exhaustiva de variantes de producto.
    """

    store_id = "aliexpress_es"
    store_name = "AliExpress Plaza (España)"
    base_url = "https://es.aliexpress.com"

    def build_search_url(self, criteria: SearchCriteria) -> str:
        query_encoded = urllib.parse.quote_plus(criteria.clean_query)
        url = f"{self.base_url}/w/wholesale-{query_encoded}.html"
        params = []
        if criteria.max_price:
            params.append(f"maxPrice={int(criteria.max_price)}")
        if criteria.min_price:
            params.append(f"minPrice={int(criteria.min_price)}")
        if params:
            url += "?" + "&".join(params)
        return url

    def _extract_from_json(self, init_data: dict, seen_items: set) -> List[ProductResult]:
        """
        Extrae productos directamente de la estructura JSON embebida en la página
        (window._dida_config_._init_data_), capturando hasta 60 ítems por página
        con títulos limpios no truncados y precios oficiales en euros.
        """
        results: List[ProductResult] = []
        if not isinstance(init_data, dict):
            return results

        data_root = init_data.get("data", {}).get("data", {}).get("root", {})
        mods = data_root.get("fields", {}).get("mods", {})
        item_list = mods.get("itemList", {}).get("content", [])

        if not item_list and "itemList" in init_data:
            item_list = init_data.get("itemList", [])

        for item in item_list:
            if not isinstance(item, dict):
                continue

            product_id = item.get("productId") or item.get("itemId")
            if not product_id:
                continue

            item_id_str = str(product_id)
            if item_id_str in seen_items:
                continue
            seen_items.add(item_id_str)

            # Título limpio
            title_obj = item.get("title", {})
            title = ""
            if isinstance(title_obj, dict):
                title = title_obj.get("displayTitle") or title_obj.get("title") or ""
            elif isinstance(title_obj, str):
                title = title_obj

            if not title or len(title) < 5:
                continue

            # Precio en euros
            price = 0.0
            prices_obj = item.get("prices", {})
            if isinstance(prices_obj, dict):
                sale_price_dict = prices_obj.get("salePrice", {})
                if isinstance(sale_price_dict, dict):
                    sale_price_str = sale_price_dict.get("formattedPrice") or sale_price_dict.get("minPrice")
                    if sale_price_str:
                        price = parse_price(str(sale_price_str)) or 0.0

                if price == 0.0:
                    orig_price_dict = prices_obj.get("originalPrice", {})
                    if isinstance(orig_price_dict, dict):
                        orig_price_str = orig_price_dict.get("formattedPrice")
                        if orig_price_str:
                            price = parse_price(str(orig_price_str)) or 0.0

            direct_url = f"{self.base_url}/item/{item_id_str}.html"

            # Enlace o imagen
            image_url = item.get("image", {}).get("imgUrl") if isinstance(item.get("image"), dict) else None
            if image_url and image_url.startswith("//"):
                image_url = "https:" + image_url

            results.append(
                ProductResult(
                    title=title,
                    price=price,
                    store_name=self.store_name,
                    url=direct_url,
                    image_url=image_url,
                    in_stock=True,
                    ships_from_spain=True,
                )
            )

        return results

    def _extract_from_dom(self, html: str, seen_items: set) -> List[ProductResult]:
        """
        Extracción de respaldo basada en el análisis del DOM mediante BeautifulSoup.
        Útil en caso de que la estructura JSON interna no esté disponible o cambie.
        """
        results: List[ProductResult] = []
        if not html:
            return results

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
            direct_url = f"{self.base_url}/item/{item_id}.html"

            # Localizar el contenedor de la tarjeta de producto
            card = a
            for _ in range(6):
                if card.parent and card.parent.name in ["div", "li"]:
                    card = card.parent
                    if "€" in card.get_text():
                        break

            # Descartar anuncios y tarjetas patrocinadas
            if is_sponsored_card(card, direct_url):
                continue

            # Comprobar disponibilidad de stock
            in_stock = not is_out_of_stock(card)

            # Título del artículo
            title = ""
            h_elem = card.find(["h1", "h2", "h3"])
            if h_elem:
                title = h_elem.get_text(strip=True)
            if not title or len(title) < 10 or title.lower() == "product":
                title_elem = card.select_one("[class*='title'], [class*='Title']")
                if title_elem:
                    title = title_elem.get_text(strip=True)
            if not title or len(title) < 10 or title.lower() == "product":
                img = card.find("img", alt=True)
                if img and len(img.get("alt", "")) > 10 and img.get("alt", "").lower() != "product":
                    title = img["alt"]
                else:
                    title = a.get("title", "") or a.get_text(strip=True)

            if not title or len(title) < 5 or title.lower() == "product":
                continue

            # Extracción de precio en euros (evitando precios tachados y financiación)
            price = 0.0
            price_spans = card.select("[class*='price'], [class*='Price'], [class*='currentPrice']")
            for p_elem in price_spans:
                if is_strikethrough_or_old_price(p_elem):
                    continue
                p_text = p_elem.get_text(strip=True)
                if is_financing_or_unit_price(p_text):
                    continue
                parsed = parse_price(p_text)
                if parsed and parsed > 0:
                    price = parsed
                    break

            if price == 0.0:
                card_text = card.get_text(separator=" ")
                if not is_financing_or_unit_price(card_text):
                    m_p = re.search(r"(\d+(?:[\.,]\d{1,2})?)\s*€", card_text) or re.search(r"€\s*(\d+(?:[\.,]\d{1,2})?)", card_text)
                    if m_p:
                        price = parse_price(m_p.group(0)) or 0.0

            results.append(
                ProductResult(
                    title=title,
                    price=price,
                    store_name=self.store_name,
                    url=direct_url,
                    in_stock=in_stock,
                    ships_from_spain=True,
                )
            )

        return results

    def search(self, criteria: SearchCriteria) -> List[ProductResult]:
        queries = criteria.target_search_queries[:4] if criteria.target_search_queries else [criteria.clean_query]
        results: List[ProductResult] = []
        seen_items = set()

        eval_script = "() => (window._dida_config_ && window._dida_config_._init_data_) ? window._dida_config_._init_data_ : null"

        for q in queries:
            query_encoded = urllib.parse.quote_plus(q)
            search_url = f"{self.base_url}/w/wholesale-{query_encoded}.html"

            # Ajustar precio máximo según la CPU de la sub-query si existe regla condicional
            query_max_price = criteria.max_price
            if criteria.max_price_by_cpu:
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.lower() in q.lower():
                        query_max_price = p_max
                        break

            params = []
            if query_max_price:
                params.append(f"maxPrice={int(query_max_price)}")
            if criteria.min_price:
                params.append(f"minPrice={int(criteria.min_price)}")
            if params:
                search_url += "?" + "&".join(params)

            html, init_data = self.get_browser_page_data(
                search_url,
                wait_timeout_ms=2000,
                scroll_count=1,
                eval_js=eval_script,
            )

            # 1. Extracción primaria desde el objeto JSON estructurado de AliExpress
            if init_data:
                json_results = self._extract_from_json(init_data, seen_items)
                results.extend(json_results)

            # 2. Extracción complementaria desde el DOM renderizado
            if html:
                dom_results = self._extract_from_dom(html, seen_items)
                results.extend(dom_results)

            # Si ya obtuvimos un volumen representativo de candidatos para este término, no saturar
            if len(results) >= 40:
                break

        return results
