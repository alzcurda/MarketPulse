import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from marketpulse.web.app import app
from marketpulse.models import ProductResult, DiscardReason, SearchCriteria, ProductCategory


class TestWebAPI(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_get_status(self):
        resp = self.client.get("/api/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "online")
        self.assertEqual(data["app_name"], "MarketPulse")
        self.assertTrue(len(data["available_stores"]) >= 5)

    def test_serve_index_html(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("MarketPulse", resp.text)
        self.assertIn("Buscador de Chollos", resp.text)

    def test_analyze_empty_query_returns_400(self):
        resp = self.client.post("/api/analyze", json={"query": "   "})
        self.assertEqual(resp.status_code, 400)

    @patch("marketpulse.core.llm_client.LLMClient.analyze_query", return_value=None)
    def test_analyze_valid_prompt(self, mock_llm):
        resp = self.client.post("/api/analyze", json={"query": "gmktec g10 mini pc"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["product_type"], "mini_pc")
        self.assertTrue(len(data["refinement_aspects"]) > 0)
        self.assertTrue(len(data["recommended_stores"]) > 0)
        self.assertTrue(len(data["all_stores"]) >= 5)

    @patch("marketpulse.web.app._execute_store_search")
    def test_search_endpoint(self, mock_store_search):
        mock_store_search.return_value = [
            ProductResult(
                title="GMKtec G10 Mini PC AMD Ryzen 5 16GB RAM 512GB SSD",
                price=219.0,
                store_name="AliExpress",
                url="https://aliexpress.com/item/123",
                in_stock=True,
                ships_from_spain=True,
            )
        ]

        payload = {
            "raw_query": "gmktec g10 mini pc",
            "clean_query": "gmktec g10 mini pc",
            "category": "tecnologia_general",
            "product_type": "mini_pc",
            "product_type_label": "Mini PC",
            "target_brand": "GMKtec",
            "target_model": "G10",
            "target_models": ["G10"],
            "min_ram_gb": 16,
            "min_storage_gb": 512,
            "selected_stores": ["aliexpress_es"],
            "selected_refinements": {"ram": "16 GB"}
        }

        resp = self.client.post("/api/search", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total_valid"], 1)
        self.assertEqual(len(data["products"]), 1)
        self.assertEqual(data["products"][0]["store_name"], "AliExpress")
        self.assertEqual(data["products"][0]["price"], 219.0)

    def test_correct_endpoint(self):
        payload = {
            "current_query": "Mini pc TRIGKEY Green G4 Intel",
            "correction": "la marca es Trigkey y el modelo es solo Green G4",
            "current_brand": "Trigkey",
            "current_models": ["Green G4", "Trigkey G4"]
        }
        resp = self.client.post("/api/correct", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["target_brand"], "Trigkey")
        self.assertEqual(data["target_models"], ["Green G4"])


if __name__ == "__main__":
    unittest.main()
