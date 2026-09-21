import unittest
from unittest.mock import patch
from marketpulse.models import ProductCategory, SearchCriteria
from marketpulse.core.store_router import StoreRouter
from marketpulse.stores.wallapop import WallapopProvider


class TestWallapopProvider(unittest.TestCase):

    def setUp(self):
        self.provider = WallapopProvider()
        self.router = StoreRouter()

    def test_build_search_url(self):
        criteria = SearchCriteria(
            raw_query="mini pc beelink n100",
            clean_query="mini pc beelink n100",
            min_price=150.0,
            max_price=300.0,
        )
        url = self.provider.build_search_url(criteria)
        self.assertIn("keywords=mini+pc+beelink+n100", url)
        self.assertIn("min_sale_price=150", url)
        self.assertIn("max_sale_price=300", url)

    def test_router_includes_wallapop(self):
        recs = self.router.recommend_stores(ProductCategory.PC_COMPONENTS)
        store_ids = [r.store_id for r in recs]
        self.assertIn("wallapop", store_ids)

        wallapop_rec = next(r for r in recs if r.store_id == "wallapop")
        self.assertTrue(wallapop_rec.enabled_by_default)
        self.assertEqual(wallapop_rec.store_name, "Wallapop (Segunda Mano)")
        self.assertIn("Wallapop Envíos", wallapop_rec.reason)

    @patch.object(WallapopProvider, "get_browser_html")
    def test_search_parsing_articles(self, mock_get_html):
        mock_html = """
        <html>
        <body>
            <article class="retrieval-item-card-module_RetrievalItemCard__ckj4h">
                <div class="retrieval-item-card-module_RetrievalItemCard__content__nA7gw">
                    <a class="retrieval-item-card-module_RetrievalItemCard__titleLink__cvSDT" href="/item/mini-pc-beelink-ryzen-9-1300738205">
                        <h3 class="retrieval-item-card-module_RetrievalItemCard__title__GjAq9">Mini PC Beelink Ryzen 9</h3>
                    </a>
                    <div class="retrieval-item-card-module_RetrievalItemCard__price__zXvlG">
                        <span aria-label="Current price" class="retrieval-item-card-module_RetrievalItemCard__currentPrice__mOTcZ">270,00 €</span>
                    </div>
                    <wallapop-badge badge-type="shippingAvailable" text="Envío disponible"></wallapop-badge>
                </div>
            </article>
            <article class="retrieval-item-card-module_RetrievalItemCard__ckj4h">
                <div class="retrieval-item-card-module_RetrievalItemCard__content__nA7gw">
                    <a class="retrieval-item-card-module_RetrievalItemCard__titleLink__cvSDT" href="/item/beelink-mini-s12-pro-1301285619">
                        <h3 class="retrieval-item-card-module_RetrievalItemCard__title__GjAq9">Beelink Mini S12 Pro N100 16GB</h3>
                    </a>
                    <div class="retrieval-item-card-module_RetrievalItemCard__price__zXvlG">
                        <span aria-label="Current price" class="retrieval-item-card-module_RetrievalItemCard__currentPrice__mOTcZ">160 €</span>
                    </div>
                </div>
            </article>
        </body>
        </html>
        """
        mock_get_html.return_value = mock_html

        criteria = SearchCriteria(
            raw_query="beelink mini pc",
            clean_query="beelink mini pc",
        )
        results = self.provider.search(criteria)

        self.assertEqual(len(results), 2)

        # Primer producto
        p1 = results[0]
        self.assertEqual(p1.title, "Mini PC Beelink Ryzen 9")
        self.assertEqual(p1.price, 270.0)
        self.assertEqual(p1.store_name, "Wallapop (Segunda Mano)")
        self.assertEqual(p1.url, "https://es.wallapop.com/item/mini-pc-beelink-ryzen-9-1300738205")
        self.assertTrue(p1.in_stock)
        self.assertTrue(p1.ships_from_spain)

        # Segundo producto
        p2 = results[1]
        self.assertEqual(p2.title, "Beelink Mini S12 Pro N100 16GB")
        self.assertEqual(p2.price, 160.0)


if __name__ == "__main__":
    unittest.main()
