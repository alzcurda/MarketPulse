import unittest
from marketpulse.core.store_router import StoreRouter
from marketpulse.models import ProductCategory


class TestStoreRouter(unittest.TestCase):

    def setUp(self):
        self.router = StoreRouter()

    def test_laptop_recommendations_prioritize_pccomponentes(self):
        recs = self.router.recommend_stores(ProductCategory.LAPTOPS)
        self.assertGreater(len(recs), 0)
        # La primera recomendación para portátiles en España debe ser PcComponentes
        top_store = recs[0]
        self.assertEqual(top_store.store_id, "pccomponentes")
        self.assertEqual(top_store.priority, 1)
        self.assertTrue(top_store.enabled_by_default)

    def test_components_recommendations(self):
        recs = self.router.recommend_stores(ProductCategory.PC_COMPONENTS)
        store_ids = [r.store_id for r in recs if r.enabled_by_default]
        self.assertIn("pccomponentes", store_ids)
        self.assertIn("amazon_es", store_ids)

    def test_shipping_info_present(self):
        recs = self.router.recommend_stores(ProductCategory.SMARTPHONES)
        for r in recs:
            self.assertTrue(len(r.shipping_info) > 0)
            self.assertTrue(len(r.estimated_delivery_days) > 0)


if __name__ == "__main__":
    unittest.main()
