import unittest
from marketpulse.core.aggregator import Aggregator
from marketpulse.models import ProductCategory, ProductResult, SearchCriteria


class TestAggregator(unittest.TestCase):

    def setUp(self):
        self.aggregator = Aggregator()
        self.criteria = SearchCriteria(
            raw_query="Portátil 16GB RAM hasta 800€",
            clean_query="portatil 16gb",
            category=ProductCategory.LAPTOPS,
            max_price=800.0,
            key_specs=["16GB RAM"]
        )

    def test_filter_exceeds_max_price(self):
        products = [
            ProductResult(
                title="Portátil Lenovo 16GB RAM",
                price=750.0,
                store_name="PcComponentes",
                url="https://example.com/p1",
                ships_from_spain=True
            ),
            ProductResult(
                title="Portátil Caro 16GB RAM",
                price=950.0,  # Superior al límite de 800€
                store_name="Amazon España",
                url="https://example.com/p2",
                ships_from_spain=True
            )
        ]

        filtered = self.aggregator.filter_and_rank(products, self.criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Portátil Lenovo 16GB RAM")

    def test_deduplication_by_url(self):
        products = [
            ProductResult(
                title="Portátil HP 15",
                price=600.0,
                store_name="PcComponentes",
                url="https://example.com/item1"
            ),
            ProductResult(
                title="Portátil HP 15 duplicado",
                price=600.0,
                store_name="PcComponentes",
                url="https://example.com/item1"
            )
        ]

        filtered = self.aggregator.filter_and_rank(products, self.criteria)
        self.assertEqual(len(filtered), 1)

    def test_accessory_exclusion(self):
        # Si buscamos portátiles, accesorios como fundas o pegatinas deben descartarse
        products = [
            ProductResult(
                title="Funda para portátil 15.6 pulgadas",
                price=19.99,
                store_name="Amazon España",
                url="https://example.com/funda"
            ),
            ProductResult(
                title="Portátil Asus VivoBook 16GB RAM",
                price=699.0,
                store_name="PcComponentes",
                url="https://example.com/asus"
            )
        ]

        filtered = self.aggregator.filter_and_rank(products, self.criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Portátil Asus VivoBook 16GB RAM")


if __name__ == "__main__":
    unittest.main()
