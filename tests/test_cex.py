import unittest
from unittest.mock import patch
from marketpulse.models import ProductCategory, SearchCriteria
from marketpulse.core.store_router import StoreRouter
from marketpulse.stores.cex_es import CexProvider


class TestCexProvider(unittest.TestCase):

    def setUp(self):
        self.provider = CexProvider()
        self.router = StoreRouter()

    def test_build_search_url(self):
        criteria = SearchCriteria(
            raw_query="mini pc hp elitedesk",
            clean_query="mini pc hp elitedesk",
        )
        url = self.provider.build_search_url(criteria)
        self.assertIn("search?stext=mini+pc+hp+elitedesk", url)

    def test_router_includes_cex(self):
        recs = self.router.recommend_stores(ProductCategory.PC_COMPONENTS)
        store_ids = [r.store_id for r in recs]
        self.assertIn("cex_es", store_ids)

        cex_rec = next(r for r in recs if r.store_id == "cex_es")
        self.assertTrue(cex_rec.enabled_by_default)
        self.assertEqual(cex_rec.store_name, "CeX Webuy (Segunda Mano)")
        self.assertIn("5 años de garantía", cex_rec.reason)

    @patch.object(CexProvider, "get_browser_html")
    def test_search_parsing_cards(self, mock_get_html):
        mock_html = """
        <html>
        <body>
            <div class="cx-card cx-card-product vertical">
                <div class="content">
                    <div class="card-title">
                        <a href="/product-detail?id=SSOBHP600G177B&categoryName=PC-SOBREMESA-WINDOWS" title="HP 600 G1 Mini PC i5 12GB 160GB">
                            HP 600 G1 Mini PC i5 12GB 160GB
                        </a>
                    </div>
                    <div class="product-prices">
                        <p class="product-main-price">95.00 €</p>
                    </div>
                </div>
            </div>
            <div class="cx-card cx-card-product vertical">
                <div class="content">
                    <div class="card-title">
                        <a href="/product-detail?id=SSOBHUIH8098A" title="Huidun H80 Mini PC Ryzen 5 16GB 512GB">
                            Huidun H80 Mini PC Ryzen 5 16GB 512GB
                        </a>
                    </div>
                    <div class="product-prices">
                        <p class="product-main-price">270.00 €</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        mock_get_html.return_value = mock_html

        criteria = SearchCriteria(
            raw_query="mini pc",
            clean_query="mini pc",
            max_price=200.0,
        )
        results = self.provider.search(criteria)

        # El segundo (270€) se filtra por max_price = 200€
        self.assertEqual(len(results), 1)
        p = results[0]
        self.assertEqual(p.title, "HP 600 G1 Mini PC i5 12GB 160GB")
        self.assertEqual(p.price, 95.0)
        self.assertEqual(p.store_name, "CeX Webuy (Segunda Mano)")
        self.assertIn("SSOBHP600G177B", p.url)
        self.assertTrue(p.in_stock)
        self.assertTrue(p.ships_from_spain)


if __name__ == "__main__":
    unittest.main()
