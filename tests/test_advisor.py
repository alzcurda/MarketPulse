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

    def test_complex_prompt_with_exclusions(self):
        prompt = (
            "Busca únicamente mini PCs con procesador Intel N100, N150, i3-1215U, i3-1315U o i3-N305, "
            "que tengan como mínimo 16 GB de RAM y al menos 512 GB o 1 TB de SSD, con envío nacional o desde la Unión Europea, "
            "descartando por completo cualquier equipo con procesador AMD o Ryzen, procesadores Intel Core de generaciones 10 u 11 o anteriores, "
            "Celeron o Pentium antiguos como J4125 o N5095, configuraciones de 8 GB de RAM o 256 GB de disco, "
            "productos de Amazon US o importaciones fuera de la UE, con un precio máximo de 230 € para N100/N150 y hasta 330 € para los Core i3."
        )
        criteria = self.advisor.analyze_user_prompt(prompt)

        # Validar CPUs permitidas
        self.assertIn("N100", criteria.allowed_cpus)
        self.assertIn("N150", criteria.allowed_cpus)
        self.assertIn("I3-1215U", criteria.allowed_cpus)

        # Validar límites de hardware
        self.assertEqual(criteria.min_ram_gb, 16)
        self.assertEqual(criteria.min_storage_gb, 512)

        # Validar exclusiones
        self.assertIn("amd", criteria.exclude_keywords)
        self.assertIn("ryzen", criteria.exclude_keywords)
        self.assertIn("celeron", criteria.exclude_keywords)
        self.assertIn("j4125", criteria.exclude_keywords)
        self.assertIn("8gb", criteria.exclude_keywords)

        # Validar precios condicionales
        self.assertEqual(criteria.max_price_by_cpu.get("N100"), 230.0)
        self.assertEqual(criteria.max_price_by_cpu.get("I3"), 330.0)
        self.assertEqual(criteria.max_price, 330.0)

        # Validar que palabras excluidas no estén en clean_query
        self.assertNotIn("amd", criteria.clean_query.lower())
        self.assertNotIn("ryzen", criteria.clean_query.lower())
        self.assertNotIn("celeron", criteria.clean_query.lower())


if __name__ == "__main__":
    unittest.main()
