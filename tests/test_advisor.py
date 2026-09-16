import unittest
from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.models import ProductCategory


class TestCriteriaAdvisor(unittest.TestCase):

    def setUp(self):
        self.advisor = CriteriaAdvisor()

    def test_detect_category_laptops(self):
        prompt = "Quiero un portátil para programar con buena batería"
        cat = self.advisor.detect_category(prompt)
        self.assertEqual(cat, ProductCategory.LAPTOPS)

    def test_detect_category_components(self):
        prompt = "Necesito una tarjeta gráfica para jugar en 2K"
        cat = self.advisor.detect_category(prompt)
        self.assertEqual(cat, ProductCategory.PC_COMPONENTS)

    def test_extract_budget_under(self):
        prompt = "Busco un ordenador portátil por menos de 800€"
        min_p, max_p = self.advisor.extract_budget(prompt)
        self.assertIsNone(min_p)
        self.assertEqual(max_p, 800.0)

    def test_extract_budget_range(self):
        prompt = "Portátil entre 600 y 900 euros"
        min_p, max_p = self.advisor.extract_budget(prompt)
        self.assertEqual(min_p, 600.0)
        self.assertEqual(max_p, 900.0)

    def test_extract_specs(self):
        prompt = "Portátil con 16GB RAM y una RTX 4060 o procesador i7"
        specs = self.advisor.extract_key_specs(prompt)
        self.assertTrue(any("16GB" in s for s in specs))
        self.assertTrue(any("RTX 4060" in s for s in specs))
        self.assertTrue(any("I7" in s for s in specs))

    def test_clean_search_query(self):
        prompt = "Hola quiero un portátil para trabajar que tenga 16gb de ram y cueste menos de 700€"
        clean = self.advisor.clean_search_query(prompt, ProductCategory.LAPTOPS)
        # Debe eliminar palabras de relleno como 'hola', 'quiero', 'menos de 700€', etc.
        self.assertNotIn("hola", clean)
        self.assertNotIn("quiero", clean)
        self.assertNotIn("menos", clean)
        self.assertIn("portatil", clean)


if __name__ == "__main__":
    unittest.main()
