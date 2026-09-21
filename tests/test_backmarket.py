import unittest
from unittest.mock import patch
from marketpulse.models import ProductCategory, SearchCriteria
from marketpulse.core.store_router import StoreRouter
from marketpulse.stores.backmarket_es import BackMarketProvider


class TestBackMarketProvider(unittest.TestCase):

    def setUp(self):
        self.provider = BackMarketProvider()
        self.router = StoreRouter()

    def test_build_search_url(self):
        criteria = SearchCriteria(
            raw_query="mini pc fujitsu",
            clean_query="mini pc fujitsu",
            min_price=100.0,
            max_price=350.0,
        )
        url = self.provider.build_search_url(criteria)
        self.assertIn("q=mini+pc+fujitsu", url)
        self.assertIn("min_price=100", url)
        self.assertIn("max_price=350", url)

    def test_router_includes_backmarket(self):
        recs = self.router.recommend_stores(ProductCategory.PC_COMPONENTS)
        store_ids = [r.store_id for r in recs]
        self.assertIn("backmarket_es", store_ids)

        bm_rec = next(r for r in recs if r.store_id == "backmarket_es")
        self.assertTrue(bm_rec.enabled_by_default)
        self.assertEqual(bm_rec.store_name, "Back Market (Reacondicionado)")
        self.assertIn("2 años de garantía", bm_rec.reason)

    @patch.object(BackMarketProvider, "get_browser_html")
    def test_search_parsing_cards(self, mock_get_html):
        mock_html = """
        <html>
        <body>
            <div class="product-card-container">
                <a href="/es-es/p/fujitsu-esprimo-q558-mini-pc-core-i5/abc123">
                    <span class="body-1-bold line-clamp-2">Fujitsu Esprimo Q558 Mini-PC Core i5 8GB 256GB SSD</span>
                </a>
                <div data-qa="productCardPrice">
                    <p class="label-medium-bold">
                        <span class="heading-2">228,44 €</span>
                    </p>
                    <s>500,00 € nuevo</s>
                </div>
            </div>
            <div class="product-card-container">
                <a href="/es-es/p/hp-elitedesk-800-g4-mini-pc/def456">
                    <span class="body-1-bold line-clamp-2">HP EliteDesk 800 G4 Desktop Mini PC Core i5 16GB 512GB</span>
                </a>
                <div data-qa="productCardPrice">
                    <p class="label-medium-bold">
                        <span class="heading-2">292,23 €</span>
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        mock_get_html.return_value = mock_html

        criteria = SearchCriteria(
            raw_query="mini pc",
            clean_query="mini pc",
            max_price=250.0,
        )
        results = self.provider.search(criteria)

        # El segundo (292.23€) se filtra por max_price = 250€
        self.assertEqual(len(results), 1)
        p = results[0]
        self.assertEqual(p.title, "Fujitsu Esprimo Q558 Mini-PC Core i5 8GB 256GB SSD")
        self.assertEqual(p.price, 228.44)
        self.assertEqual(p.store_name, "Back Market (Reacondicionado)")
        self.assertIn("/es-es/p/fujitsu-esprimo-q558", p.url)
        self.assertTrue(p.in_stock)
        self.assertTrue(p.ships_from_spain)


if __name__ == "__main__":
    unittest.main()
