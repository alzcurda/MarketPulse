import unittest
from unittest.mock import patch
from marketpulse.core.aggregator import Aggregator
from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.models import DiscardReason, ProductCategory, ProductResult, SearchCriteria


class TestDiscardVerification(unittest.TestCase):

    def setUp(self):
        self.aggregator = Aggregator()
        self.advisor = CriteriaAdvisor()
        self.patcher = patch("marketpulse.core.llm_client.LLMClient.analyze_query", return_value=None)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_multi_model_extraction(self):
        prompt = "Mini PC GMKtec, modelos NucBox G3, G5, M5 o M6."
        criteria = self.advisor.analyze_user_prompt(prompt)

        self.assertIsNotNone(criteria.target_model)
        self.assertIn("NucBox G3", criteria.target_models)
        self.assertIn("NucBox G5", criteria.target_models)
        self.assertIn("NucBox M5", criteria.target_models)
        self.assertIn("NucBox M6", criteria.target_models)

        # Verificar variantes normalizadas
        self.assertIn("nucbox g3", criteria.target_model_variants)
        self.assertIn("nucbox g5", criteria.target_model_variants)
        self.assertIn("nucbox m5", criteria.target_model_variants)
        self.assertIn("nucbox m6", criteria.target_model_variants)
        # Variantes con la marca detectada
        self.assertIn("gmktec g3", criteria.target_model_variants)
        self.assertIn("gmktec g5", criteria.target_model_variants)

    def test_discard_records_generation_and_summary(self):
        criteria = SearchCriteria(
            raw_query="Mini PC GMKtec NucBox G3",
            clean_query="mini pc gmktec nucbox g3",
            category=ProductCategory.PC_COMPONENTS,
            max_price=300.0,
            target_model="NucBox G3",
            target_models=["NucBox G3"],
            target_model_variants=["nucbox g3", "nucbox-g3", "nucboxg3"],
            min_score_threshold=80.0
        )

        candidates = [
            # 1. Pasa los filtros
            ProductResult(
                title="GMKtec NucBox G3 Intel N100 16GB RAM 512GB SSD",
                price=199.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/item1",
                in_stock=True,
                ships_from_spain=True
            ),
            # 2. Descarte por modelo diferente
            ProductResult(
                title="Beelink Mini S12 Pro Intel N100 16GB RAM 500GB SSD",
                price=189.0,
                store_name="PcComponentes",
                url="https://pccomponentes.com/item2",
                in_stock=True,
                ships_from_spain=True
            ),
            # 3. Descarte por CPU antigua (Core i3 10ª gen)
            ProductResult(
                title="GMKtec NucBox G3 con Intel Core i3-10110U 16GB 512GB",
                price=250.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/item3",
                in_stock=True,
                ships_from_spain=True
            ),
            # 4. Descarte por accesorio
            ProductResult(
                title="Funda soporte vesa para GMKtec NucBox G3",
                price=15.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/item4",
                in_stock=True,
                ships_from_spain=True
            ),
            # 5. Descarte por superar presupuesto
            ProductResult(
                title="GMKtec NucBox G3 32GB RAM 1TB SSD",
                price=380.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/item5",
                in_stock=True,
                ships_from_spain=True
            ),
            # 6. Descarte por sin stock
            ProductResult(
                title="GMKtec NucBox G3 Edición Especial",
                price=210.0,
                store_name="Amazon España",
                url="https://amazon.es/dp/item6",
                in_stock=False,
                ships_from_spain=True
            ),
        ]

        filtered = self.aggregator.filter_and_rank(candidates, criteria)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].title, "GMKtec NucBox G3 Intel N100 16GB RAM 512GB SSD")

        # Verificar que se registraron 5 descartes
        discards = self.aggregator.last_discard_records
        self.assertEqual(len(discards), 5)

        # Verificar los motivos registrados
        reasons = [d.reason for d in discards]
        self.assertIn(DiscardReason.TARGET_MODEL_MISMATCH, reasons)
        self.assertIn(DiscardReason.OLD_INTEL_CORE, reasons)
        self.assertIn(DiscardReason.ACCESSORY, reasons)
        self.assertIn(DiscardReason.PRICE_ABOVE_MAX, reasons)
        self.assertIn(DiscardReason.OUT_OF_STOCK, reasons)

        # Verificar resumen agrupado
        summary = self.aggregator.get_discard_summary()
        self.assertEqual(summary[DiscardReason.TARGET_MODEL_MISMATCH.value], 1)
        self.assertEqual(summary[DiscardReason.OLD_INTEL_CORE.value], 1)
        self.assertEqual(summary[DiscardReason.ACCESSORY.value], 1)
        self.assertEqual(summary[DiscardReason.PRICE_ABOVE_MAX.value], 1)
        self.assertEqual(summary[DiscardReason.OUT_OF_STOCK.value], 1)


if __name__ == "__main__":
    unittest.main()
