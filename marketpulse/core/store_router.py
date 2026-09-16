from typing import Dict, List
from marketpulse.models import ProductCategory, StoreRecommendation


class StoreRouter:
    """
    Enrutador inteligente especializado en el ecosistema de comercio electrónico en España.
    Asocia la categoría del producto buscado con las mejores opciones de tiendas locales
    o con almacén en España, indicando los motivos, tiempos estimados y prioridad.
    """

    STORE_CATALOG: Dict[str, Dict] = {
        "pccomponentes": {
            "name": "PcComponentes",
            "shipping_info": "Envío nacional desde Murcia (Península y Baleares)",
            "estimated_delivery_days": "24 - 48 horas",
            "trust_score": 9.5,
            "strengths": [ProductCategory.LAPTOPS, ProductCategory.PC_COMPONENTS, ProductCategory.MONITORS, ProductCategory.GAMING],
        },
        "amazon_es": {
            "name": "Amazon España",
            "shipping_info": "Centros logísticos en España (Prime disponible)",
            "estimated_delivery_days": "24 horas (Prime) / 48 - 72 horas",
            "trust_score": 9.3,
            "strengths": [ProductCategory.LAPTOPS, ProductCategory.SMARTPHONES, ProductCategory.AUDIO, ProductCategory.HOME_APPLIANCES, ProductCategory.GENERAL_TECH],
        },
        "mediamarkt": {
            "name": "MediaMarkt España",
            "shipping_info": "Envío a domicilio o recogida inmediata en tienda física",
            "estimated_delivery_days": "24 - 48 horas / 2h en tienda",
            "trust_score": 8.8,
            "strengths": [ProductCategory.SMARTPHONES, ProductCategory.HOME_APPLIANCES, ProductCategory.AUDIO, ProductCategory.MONITORS],
        },
        "aliexpress_es": {
            "name": "AliExpress Plaza (España)",
            "shipping_info": "Almacenes locales en España (sin aduanas ni aranceles)",
            "estimated_delivery_days": "3 - 5 días hábiles",
            "trust_score": 8.2,
            "strengths": [ProductCategory.AUDIO, ProductCategory.GENERAL_TECH, ProductCategory.GAMING, ProductCategory.PC_COMPONENTS],
        }
    }

    def recommend_stores(self, category: ProductCategory) -> List[StoreRecommendation]:
        """
        Devuelve una lista ordenada de tiendas recomendadas para la categoría dada.
        """
        recommendations: List[StoreRecommendation] = []

        for store_id, info in self.STORE_CATALOG.items():
            is_specialized = category in info["strengths"]

            if store_id == "pccomponentes":
                if is_specialized:
                    reason = "Referente líder en informática en España. Excelente servicio técnico y garantía local."
                    priority = 1
                    enabled = True
                else:
                    reason = "Buena opción en electrónica y tecnología con envío rápido nacional."
                    priority = 3
                    enabled = False

            elif store_id == "amazon_es":
                reason = "Catálogo masivo, política de devoluciones sin fricción y entrega rápida en España."
                priority = 1 if not (category == ProductCategory.PC_COMPONENTS) else 2
                enabled = True

            elif store_id == "mediamarkt":
                if is_specialized:
                    reason = "Gran disponibilidad local, ofertas web y opción de recogida o servicio en tiendas físicas."
                    priority = 2
                    enabled = True
                else:
                    reason = "Distribuidor oficial de electrónica con red física en toda España."
                    priority = 3
                    enabled = False

            elif store_id == "aliexpress_es":
                if is_specialized:
                    reason = "Canal Plaza con envío garantizado desde almacén español, ideal para encontrar precios competitivos."
                    priority = 3
                    enabled = True
                else:
                    reason = "Opción para comparar ofertas alternativas con envío local."
                    priority = 4
                    enabled = False

            recommendations.append(
                StoreRecommendation(
                    store_id=store_id,
                    store_name=info["name"],
                    reason=reason,
                    priority=priority,
                    shipping_info=info["shipping_info"],
                    estimated_delivery_days=info["estimated_delivery_days"],
                    enabled_by_default=enabled,
                )
            )

        # Ordenar por prioridad (menor número = mayor prioridad)
        recommendations.sort(key=lambda r: r.priority)
        return recommendations
