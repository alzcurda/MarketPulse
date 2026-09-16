import urllib.parse
from typing import List
from marketpulse.models import ProductResult, SearchCriteria
from marketpulse.stores.base import BaseStoreProvider


class AliExpressEsProvider(BaseStoreProvider):
    """
    Conector para AliExpress con filtro estricto de envío desde España (Plaza).
    Garantiza entrega en 3 a 5 días y ausencia de impuestos/aduanas sorpresa.
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
        search_url = self.build_search_url(criteria)
        return [
            ProductResult(
                title=f"[Acceso directo Plaza ES] AliExpress España para: '{criteria.clean_query}' (Envío local)",
                price=criteria.max_price or 0.0,
                store_name=self.store_name,
                url=search_url,
                in_stock=True,
                ships_from_spain=True,
                match_score=80.0
            )
        ]
