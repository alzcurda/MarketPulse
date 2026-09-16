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

    def test_discard_search_urls_and_placeholders(self):
        # Enlaces de búsqueda genéricos o con placeholders no deben considerarse productos
        products = [
            ProductResult(
                title="Resultados Amazon.es para 'portatil'",
                price=800.0,
                store_name="Amazon España",
                url="https://www.amazon.es/s?k=portatil"
            ),
            ProductResult(
                title="[Acceso directo Plaza ES] AliExpress España para: 'portatil'",
                price=800.0,
                store_name="AliExpress Plaza (España)",
                url="https://es.aliexpress.com/w/wholesale-portatil.html?shipFromCountry=ES"
            ),
            ProductResult(
                title="Portátil Real Lenovo IdeaPad 16GB RAM",
                price=549.0,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0XYZ12345"
            )
        ]

        filtered = self.aggregator.filter_and_rank(products, self.criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].url, "https://www.amazon.es/dp/B0XYZ12345")
        self.assertEqual(filtered[0].title, "Portátil Real Lenovo IdeaPad 16GB RAM")

    def test_strict_hardware_and_cpu_filtering(self):
        criteria = SearchCriteria(
            raw_query="Test prompt",
            clean_query="mini pc n100 16gb 512gb",
            allowed_cpus=["N100", "N150", "I3-1215U", "I3-1315U", "I3-N305", "N305"],
            min_ram_gb=16,
            min_storage_gb=512,
            exclude_keywords=["amd", "ryzen", "celeron", "pentium", "j4125", "n5095", "n2940", "amazon us"],
            max_price_by_cpu={"N100": 230.0, "N150": 230.0, "I3": 330.0},
            max_price=330.0
        )

        candidates = [
            # 1. Celeron N2940 (excluido por celeron y por n2940)
            ProductResult(
                title="Mini PC sin ventilador N2940 8 GB RAM 128 GB SSD Intel Celeron Fanless",
                price=170.21,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0HBWW4FY7"
            ),
            # 2. PELADN N100 pero solo 8GB RAM / 256GB y precio 262.40 > 230
            ProductResult(
                title="PELADN Mini PC, Intel N100 (hasta 3.4 GHz), 8 GB DDR4/256 GB SSD",
                price=262.40,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0D3WMV21G"
            ),
            # 3. Barebone sin RAM
            ProductResult(
                title="DreamQuest Mini PC Barebone N150 de 12.ª generación (hasta 3,4 GHz)",
                price=229.09,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0GX51PXSZ"
            ),
            # 4. Core i3 antiguo de 3ª generación
            ProductResult(
                title="Best small desktop PC Mi3217 Good PC Core i3-3217U Processor (3M Cache)",
                price=273.10,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B01MZ63SD8"
            ),
            # 5. Core i3 antiguo con 2G RAM
            ProductResult(
                title="Fastest Mini Computer mi3217 Mini PC i3 – 3217U 3 m Cache 2 G RAM",
                price=252.09,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B01N5F0BPV"
            ),
            # 6. AMD Ryzen (excluido)
            ProductResult(
                title="BOSGAME Mini PC E2, mini computadoras con AMD Ryzen 5 3550H, 16 GB",
                price=327.92,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0DNT28BV1"
            ),
            # 7. PRODUCTO VÁLIDO QUE SÍ CUMPLE (N100, 16GB, 512GB, <= 230€)
            ProductResult(
                title="MeLE Quieter4C Mini PC sin Ventilador N100 16GB 512GB Microordenador",
                price=229.00,
                store_name="Amazon España",
                url="https://www.amazon.es/dp/B0CNV981QH"
            )
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "MeLE Quieter4C Mini PC sin Ventilador N100 16GB 512GB Microordenador")
        self.assertEqual(filtered[0].url, "https://www.amazon.es/dp/B0CNV981QH")

    def test_unknown_price_discarded_when_budget_set(self):
        # Si el usuario establece un tope de presupuesto (ej: 330€), productos cuyo precio
        # es desconocido (0.0 / 'Ver en tienda') deben descartarse para no colar equipos de 600€
        unknown_price_prod = ProductResult(
            title="Mini PC BLEU JOUR NUC VALUE Intel Core i3-1215U 16 GB RAM 512 GB SSD",
            price=0.0,
            store_name="MediaMarkt",
            url="https://www.mediamarkt.es/es/product/example.html"
        )
        known_in_budget_prod = ProductResult(
            title="Mini PC Beelink N100 16 GB RAM 512 GB SSD",
            price=199.0,
            store_name="Amazon España",
            url="https://www.amazon.es/dp/B0EX"
        )

        criteria = SearchCriteria(
            raw_query="mini pc i3 o n100 16gb 512gb hasta 330€",
            clean_query="mini pc 16gb 512gb",
            max_price=330.0,
            allowed_cpus=["I3-1215U", "N100"],
            min_ram_gb=16,
            min_storage_gb=512
        )

        filtered = self.aggregator.filter_and_rank([unknown_price_prod, known_in_budget_prod], criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Mini PC Beelink N100 16 GB RAM 512 GB SSD")
        self.assertEqual(filtered[0].price, 199.0)


if __name__ == "__main__":
    unittest.main()
