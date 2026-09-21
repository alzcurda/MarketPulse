import unittest
from unittest.mock import patch, MagicMock
from marketpulse.core.llm_client import LLMClient
from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.models import SearchCriteria, ProductCategory


class TestLLMClient(unittest.TestCase):

    def setUp(self):
        LLMClient._cached_backend = None
        LLMClient._cached_backend_label = None

    def test_json_cleaner_handles_codeblocks(self):
        sample = '```json\n{"product_type": "Cafetera", "is_generic": true}\n```'
        result = LLMClient._clean_json_response(sample)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("product_type"), "Cafetera")
        self.assertTrue(result.get("is_generic"))

    def test_json_cleaner_handles_raw_json(self):
        sample = '{"product_type": "Taladro", "is_generic": false}'
        result = LLMClient._clean_json_response(sample)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("product_type"), "Taladro")

    def test_json_cleaner_handles_dirty_surrounding_text(self):
        sample = 'Aquí tienes el análisis:\n{"product_type": "Monitor", "is_generic": true}\nEspero te sirva.'
        result = LLMClient._clean_json_response(sample)
        self.assertIsNotNone(result)
        self.assertEqual(result.get("product_type"), "Monitor")

    @patch("marketpulse.core.llm_client.config")
    def test_backend_none_when_disabled(self, mock_config):
        mock_config.LLM_BACKEND = "none"
        backend, label = LLMClient.get_backend_info()
        self.assertEqual(backend, "none")
        self.assertIn("Sin IA", label)

    @patch("marketpulse.core.llm_client.config")
    def test_backend_gemini_configured(self, mock_config):
        mock_config.LLM_BACKEND = "gemini"
        mock_config.GEMINI_API_KEY = "test_key"
        mock_config.GEMINI_MODEL = "gemini-1.5-flash"
        backend, label = LLMClient.get_backend_info()
        self.assertEqual(backend, "gemini")
        self.assertIn("Google Gemini", label)

    def test_criteria_refine_hardware(self):
        advisor = CriteriaAdvisor()
        crit = SearchCriteria(
            raw_query="mini pc",
            clean_query="mini pc",
            category=ProductCategory.PC_COMPONENTS,
            product_type="mini_pc",
            is_generic=True,
        )
        refined = advisor.refine_criteria(crit, {
            "barebone": "Solo equipos completos listos para usar",
            "ram": "32 GB",
            "storage": "1 TB SSD",
        })
        self.assertEqual(refined.min_ram_gb, 32)
        self.assertEqual(refined.min_storage_gb, 1024)
        self.assertIn("barebone", refined.exclude_keywords)


if __name__ == "__main__":
    unittest.main()
