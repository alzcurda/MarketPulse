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
                title="Portátil HP 15 16GB RAM",
                price=600.0,
                store_name="PcComponentes",
                url="https://example.com/item1"
            ),
            ProductResult(
                title="Portátil HP 15 16GB RAM duplicado",
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

    def test_mandatory_model_token_match(self):
        # Política de Coincidencia de Modelo Obligatoria (EQi12)
        criteria = SearchCriteria(
            raw_query="Beelink EQi12 16GB RAM 512GB SSD",
            clean_query="mini pc eqi12 16gb 512gb",
            category=ProductCategory.PC_COMPONENTS,
            target_model="EQi12",
            target_model_variants=["eqi 12", "eqi-12", "eqi12"],
            min_ram_gb=16,
            min_storage_gb=512,
            min_score_threshold=80.0
        )

        candidates = [
            # 1. Variante con guión: EQi-12 -> debe ser admitida
            ProductResult(
                title="Beelink Mini PC EQi-12 Intel Core i3-1220P 16GB RAM 512GB SSD",
                price=329.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/eqi12-dash"
            ),
            # 2. Variante con espacio: EQI 12 -> debe ser admitida
            ProductResult(
                title="Beelink EQI 12 Mini PC Intel Core i5-12450H 16GB RAM 512GB SSD",
                price=389.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/eqi12-space"
            ),
            # 3. Variante compacta: EQi12 -> debe ser admitida
            ProductResult(
                title="Beelink EQi12 Mini Ordenador Intel Core i7 16GB RAM 512GB SSD",
                price=429.0,
                store_name="AliExpress Plaza (España)",
                url="https://aliexpress.com/eqi12-compact"
            ),
            # 4. Otro modelo de la misma marca: EQ14 -> PROHIBIDO / DESCARTADO
            ProductResult(
                title="Beelink EQ14 Mini PC Intel N150 16GB RAM 512GB SSD",
                price=219.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/eq14"
            ),
            # 5. Otro modelo de la misma marca: SER5 -> PROHIBIDO / DESCARTADO
            ProductResult(
                title="Beelink SER5 Mini PC AMD Ryzen 5 5560U 16GB RAM 512GB SSD",
                price=289.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/ser5"
            ),
            # 6. Otro modelo de la misma marca: Mini S12 -> PROHIBIDO / DESCARTADO
            ProductResult(
                title="Beelink Mini S12 Pro Intel N100 16GB RAM 512GB SSD",
                price=189.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/s12pro"
            ),
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 3)
        # Verificar que solo entraron las 3 variantes exactas de EQi12
        matched_urls = [p.url for p in filtered]
        self.assertIn("https://amazon.es/dp/eqi12-dash", matched_urls)
        self.assertIn("https://pccomponentes.com/eqi12-space", matched_urls)
        self.assertIn("https://aliexpress.com/eqi12-compact", matched_urls)

    def test_empty_results_when_no_exact_model_match(self):
        # Si ninguna tienda ofrece el modelo exacto buscado, la lista resultante debe ser vacía
        criteria = SearchCriteria(
            raw_query="Beelink EQi12",
            clean_query="mini pc eqi12",
            category=ProductCategory.PC_COMPONENTS,
            target_model="EQi12",
            target_model_variants=["eqi 12", "eqi-12", "eqi12"],
            min_score_threshold=80.0
        )

        candidates = [
            ProductResult(
                title="Beelink SER5 Pro Mini PC AMD Ryzen 7 5800H 16GB RAM",
                price=320.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/ser5"
            ),
            ProductResult(
                title="Beelink EQ14 Intel Twin Lake N150 Mini PC",
                price=210.0,
                store_name="MediaMarkt",
                url="https://mediamarkt.es/eq14"
            )
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 0)

    def test_category_isolation(self):
        # En categorías de informática, productos ajenos (electrodomésticos, consolas, videojuegos) deben ser purgados
        criteria = SearchCriteria(
            raw_query="Mini PC Intel 16GB",
            clean_query="mini pc 16gb",
            category=ProductCategory.PC_COMPONENTS,
            min_score_threshold=80.0
        )

        candidates = [
            ProductResult(
                title="Campana extractora decorativa CATA 60cm acero inoxidable",
                price=149.0,
                store_name="MediaMarkt",
                url="https://mediamarkt.es/campana"
            ),
            ProductResult(
                title="Lavadora Balay 8kg 1200rpm blanco",
                price=389.0,
                store_name="MediaMarkt",
                url="https://mediamarkt.es/lavadora"
            ),
            ProductResult(
                title="Videojuego EA Sports FC 24 PS5",
                price=59.99,
                store_name="Amazon España",
                url="https://amazon.es/juego"
            ),
            ProductResult(
                title="Smartwatch Xiaomi Redmi Watch 4 pantalla AMOLED",
                price=79.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/watch"
            ),
            ProductResult(
                title="Mini PC Intel N100 16GB RAM 512GB SSD Windows 11",
                price=189.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/minipc-real"
            )
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "Mini PC Intel N100 16GB RAM 512GB SSD Windows 11")

    def test_price_vs_hardware_sanity_check(self):
        # CPUs de gama alta / profesionales (Core Ultra, i9, Ryzen 9, Ryzen AI Max) no pueden costar < 400€
        criteria = SearchCriteria(
            raw_query="Mini PC de alto rendimiento",
            clean_query="mini pc alto rendimiento",
            category=ProductCategory.PC_COMPONENTS,
            min_score_threshold=80.0
        )

        candidates = [
            # Core Ultra a 189€ -> imposible para un mini PC completo (es dock o error) -> descartar
            ProductResult(
                title="Mini PC Intel Core Ultra 7 155H 32GB RAM 1TB SSD",
                price=189.0,
                store_name="Amazon España",
                url="https://amazon.es/ultra7-cheap"
            ),
            # Core i9 a 220€ -> descartar
            ProductResult(
                title="Mini PC Intel Core i9-13900H 32GB RAM 1TB SSD",
                price=220.0,
                store_name="Amazon España",
                url="https://amazon.es/i9-cheap"
            ),
            # Ryzen AI Max a 199€ -> descartar
            ProductResult(
                title="Mini PC AMD Ryzen AI Max 395 32GB RAM",
                price=199.0,
                store_name="Amazon España",
                url="https://amazon.es/ryzen-ai-cheap"
            ),
            # Mini PC Core Ultra a precio normal de mercado (699€) -> válido
            ProductResult(
                title="Mini PC alto rendimiento Intel Core Ultra 7 155H 32GB RAM 1TB SSD",
                price=699.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/ultra7-real"
            ),
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].url, "https://pccomponentes.com/ultra7-real")

    def test_accessory_strict_filtering(self):
        # Docks, cajas vacías y soportes vesa deben descartarse automáticamente
        criteria = SearchCriteria(
            raw_query="Mini PC Intel",
            clean_query="mini pc intel",
            category=ProductCategory.PC_COMPONENTS,
            min_score_threshold=80.0
        )

        candidates = [
            ProductResult(
                title="Estación de acoplamiento Docking Station triple monitor para Mini PC",
                price=69.0,
                store_name="Amazon España",
                url="https://amazon.es/dock"
            ),
            ProductResult(
                title="Carcasa vacía de aluminio disipadora para Mini PC N100",
                price=25.0,
                store_name="AliExpress Plaza (España)",
                url="https://aliexpress.com/caja"
            ),
            ProductResult(
                title="Soporte VESA de montaje en pared para Mini PC",
                price=15.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/vesa"
            ),
            ProductResult(
                title="Mini PC Intel N100 16GB RAM 512GB SSD",
                price=199.0,
                store_name="Amazon España",
                url="https://amazon.es/minipc"
            )
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].url, "https://amazon.es/minipc")


if __name__ == "__main__":
    unittest.main()

