import unittest
from marketpulse.core.aggregator import Aggregator
from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.models import DiscardReason, ProductCategory, ProductResult, SearchCriteria


class TestProductTypeValidation(unittest.TestCase):

    def setUp(self):
        self.advisor = CriteriaAdvisor()
        self.aggregator = Aggregator()

    def test_trigkey_green_g4_detection(self):
        prompt = "mini pc trigkey green g4"
        criteria = self.advisor.analyze_user_prompt(prompt)

        # 1. Validación de tipo de producto y marca
        self.assertEqual(criteria.product_type, "mini_pc")
        self.assertEqual(criteria.product_type_label, "Mini PC / Ordenador de sobremesa compacto")
        self.assertEqual(criteria.target_brand, "Trigkey")

        # 2. Validación de modelo y serie
        self.assertEqual(criteria.target_series, "Green G4")
        self.assertIn("Green G4", criteria.target_models)

        # 3. 'g4' solo NUNCA debe estar en variantes aisladas
        self.assertNotIn("g4", criteria.target_model_variants)
        self.assertIn("green g4", criteria.target_model_variants)
        self.assertIn("trigkey green g4", criteria.target_model_variants)

        # 4. 'g4' suelto NUNCA debe ser una consulta dirigida independiente
        self.assertNotIn("g4", criteria.target_search_queries)
        self.assertTrue(any("green g4" in q for q in criteria.target_search_queries))

    def test_discard_bombillas_and_lighting(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        bulb = ProductResult(
            title="LEDKIA Bombilla LED 12V G4 1.5W 110 lm PC 4000K Blanco Neutro",
            price=1.71,
            store_name="Amazon España",
            url="https://amazon.es/dp/bulb1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([bulb], criteria)
        self.assertEqual(len(ranked), 0)

        # Verificar que se registró el descarte
        discards = self.aggregator.last_discard_records
        self.assertEqual(len(discards), 1)
        self.assertEqual(discards[0].reason, DiscardReason.CATEGORY_MISMATCH)

    def test_discard_unreasonable_price_for_mini_pc(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        cable = ProductResult(
            title="Trigkey Green G4 Mini PC Intel N100 8GB RAM",
            price=4.99,  # Demasiado bajo para ser un mini PC (< 35€)
            store_name="Amazon España",
            url="https://amazon.es/dp/cable1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([cable], criteria)
        self.assertEqual(len(ranked), 0)
        self.assertTrue(any(d.reason == DiscardReason.UNREASONABLE_PRICE for d in self.aggregator.last_discard_records))

    def test_discard_competing_brand_mismatch(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        hp_pc = ProductResult(
            title="HP ProDesk 400 G4 Mini Desktop Computer PC i5-8th 8GB RAM",
            price=179.0,
            store_name="Amazon España",
            url="https://amazon.es/dp/hp1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([hp_pc], criteria)
        self.assertEqual(len(ranked), 0)

        reasons = [d.reason for d in self.aggregator.last_discard_records]
        self.assertTrue(
            DiscardReason.TARGET_MODEL_MISMATCH in reasons or DiscardReason.BRAND_MISMATCH in reasons
        )

    def test_pass_genuine_trigkey_pc(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        trigkey_pc = ProductResult(
            title="TRIGKEY Green G4 Mini PC Intel Alder Lake N100 16GB RAM 500GB SSD W11 Pro",
            price=189.0,
            store_name="Amazon España",
            url="https://amazon.es/dp/trigkey1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([trigkey_pc], criteria)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].title, trigkey_pc.title)
        self.assertGreaterEqual(ranked[0].match_score, 80.0)

    def test_discard_ventilador_component(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        fan = ProductResult(
            title="Ventilador de refrigeración para Trigkey Green G4 Mini PC CPU Cooler",
            price=42.0,  # Precio superior a 35€ para no depender del filtro de precio mínimo
            store_name="Amazon España",
            url="https://amazon.es/dp/fan1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([fan], criteria)
        self.assertEqual(len(ranked), 0)
        reasons = [d.reason for d in self.aggregator.last_discard_records]
        self.assertTrue(
            DiscardReason.COMPONENT_OR_SPARE_PART in reasons or DiscardReason.ACCESSORY in reasons
        )

    def test_discard_raqueta_badminton(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        racket = ProductResult(
            title="Yonex Raqueta de Bádminton Astrox Green G4 grafito",
            price=59.0,
            store_name="Amazon España",
            url="https://amazon.es/dp/racket1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([racket], criteria)
        self.assertEqual(len(ranked), 0)
        reasons = [d.reason for d in self.aggregator.last_discard_records]
        self.assertIn(DiscardReason.CATEGORY_MISMATCH, reasons)

    def test_discard_raqueta_mount_bracket(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        mount = ProductResult(
            title="Soporte de montaje tipo raqueta / bracket VESA para Trigkey Mini PC",
            price=38.0,
            store_name="AliExpress Plaza",
            url="https://aliexpress.com/item/mount1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([mount], criteria)
        self.assertEqual(len(ranked), 0)
        reasons = [d.reason for d in self.aggregator.last_discard_records]
        self.assertTrue(
            DiscardReason.COMPONENT_OR_SPARE_PART in reasons or DiscardReason.ACCESSORY in reasons
        )

    def test_discard_power_supply(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        psu = ProductResult(
            title="Fuente de alimentación cargador 12V 3A para Trigkey Green G4",
            price=39.0,
            store_name="Amazon España",
            url="https://amazon.es/dp/psu1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([psu], criteria)
        self.assertEqual(len(ranked), 0)
        reasons = [d.reason for d in self.aggregator.last_discard_records]
        self.assertTrue(
            DiscardReason.COMPONENT_OR_SPARE_PART in reasons or DiscardReason.ACCESSORY in reasons
        )

    def test_pass_genuine_pc_with_silent_fan_feature(self):
        criteria = self.advisor.analyze_user_prompt("mini pc trigkey green g4")

        genuine_pc = ProductResult(
            title="TRIGKEY Green G4 Mini PC Intel N100 16GB RAM 500GB SSD con ventilador silencioso y WiFi 6",
            price=199.0,
            store_name="Amazon España",
            url="https://amazon.es/dp/trigkey_quiet1",
            in_stock=True,
            ships_from_spain=True
        )

        ranked = self.aggregator.filter_and_rank([genuine_pc], criteria)
        self.assertEqual(len(ranked), 1)
        self.assertEqual(ranked[0].title, genuine_pc.title)
        self.assertGreaterEqual(ranked[0].match_score, 80.0)

    def test_candidate_item_classification(self):
        # 1. Deporte / Raqueta
        cand_type, label = self.aggregator.classify_candidate_item("Yonex Raqueta de Bádminton Astrox Green G4")
        self.assertEqual(cand_type, "sports_equipment")
        self.assertIn("deportivo", label.lower())

        # 2. Ventilador / Refrigeración
        cand_type, label = self.aggregator.classify_candidate_item("Ventilador de refrigeración para Trigkey Green G4 Mini PC")
        self.assertEqual(cand_type, "cooling_component")
        self.assertIn("ventilador", label.lower())

        # 3. Soporte / Bracket / Raqueta de montaje
        cand_type, label = self.aggregator.classify_candidate_item("Soporte de montaje tipo raqueta / bracket VESA para Trigkey")
        self.assertEqual(cand_type, "mounting_bracket")
        self.assertIn("soporte", label.lower())

        # 4. Iluminación / Bombilla
        cand_type, label = self.aggregator.classify_candidate_item("Bombilla LED 12V G4 1.5W")
        self.assertEqual(cand_type, "lighting")

        # 5. Equipo auténtico Mini PC
        cand_type, label = self.aggregator.classify_candidate_item("TRIGKEY Green G4 Mini PC Intel N100 16GB RAM 500GB SSD")
        self.assertEqual(cand_type, "mini_pc")


if __name__ == "__main__":
    unittest.main()
