import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from marketpulse import config
from marketpulse.core.aggregator import Aggregator
from marketpulse.core.criteria_advisor import CriteriaAdvisor
from marketpulse.core.llm_client import LLMClient
from marketpulse.core.store_router import StoreRouter
from marketpulse.models import DiscardReason, ProductCategory, ProductResult, SearchCriteria
from marketpulse.stores.aliexpress_es import AliExpressEsProvider
from marketpulse.stores.amazon_es import AmazonEsProvider
from marketpulse.stores.backmarket_es import BackMarketProvider
from marketpulse.stores.cex_es import CexProvider
from marketpulse.stores.mediamarkt import MediaMarktProvider
from marketpulse.stores.pccomponentes import PcComponentesProvider
from marketpulse.stores.wallapop import WallapopProvider

logger = logging.getLogger(__name__)

# Mapa oficial de tiendas
STORE_PROVIDER_MAP = {
    "pccomponentes": PcComponentesProvider,
    "amazon_es": AmazonEsProvider,
    "mediamarkt": MediaMarktProvider,
    "aliexpress_es": AliExpressEsProvider,
    "wallapop": WallapopProvider,
    "cex_es": CexProvider,
    "backmarket_es": BackMarketProvider,
}

STORE_METADATA = {
    "pccomponentes": {"name": "PcComponentes", "tag": "Oficial España", "color": "#ff6000"},
    "amazon_es": {"name": "Amazon España", "tag": "Envío Rápido", "color": "#f59e0b"},
    "mediamarkt": {"name": "MediaMarkt", "tag": "Garantía Oficial", "color": "#ef4444"},
    "aliexpress_es": {"name": "AliExpress", "tag": "Precios Directos", "color": "#e11d48"},
    "wallapop": {"name": "Wallapop", "tag": "Segunda Mano / Chollos", "color": "#10b981"},
    "cex_es": {"name": "CeX España", "tag": "Reacondicionado 5 años gar.", "color": "#8b5cf6"},
    "backmarket_es": {"name": "Back Market", "tag": "Reacondicionado Certificado", "color": "#06b6d4"},
}

app = FastAPI(
    title="MarketPulse Web",
    description="Asistente Inteligente de Compras y Búsqueda Multitienda",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATES_DIR = Path(__file__).parent / "templates"


# ------------------------------------------------------------------------------
# Modelos de Datos API
# ------------------------------------------------------------------------------
class AnalyzeRequest(BaseModel):
    query: str = Field(..., description="Consulta en lenguaje natural o transcripción de voz")


class SearchRequest(BaseModel):
    raw_query: str
    clean_query: str
    category: str = "tecnologia_general"
    product_type: str = "general"
    product_type_label: str = ""
    target_brand: Optional[str] = None
    target_model: Optional[str] = None
    target_models: List[str] = []
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    min_ram_gb: Optional[int] = None
    min_storage_gb: Optional[int] = None
    allowed_cpus: List[str] = []
    must_have_keywords: List[str] = []
    exclude_keywords: List[str] = []
    selected_stores: List[str] = ["aliexpress_es", "amazon_es", "pccomponentes"]
    selected_refinements: Dict[str, str] = {}


# ------------------------------------------------------------------------------
# Endpoints de la API
# ------------------------------------------------------------------------------
@app.get("/api/status")
def get_system_status():
    """Devuelve el estado del sistema, motor semántico y tiendas disponibles."""
    backend_id, backend_label = LLMClient.get_backend_info()
    return {
        "status": "online",
        "app_name": config.APP_NAME,
        "backend_id": backend_id,
        "backend_label": backend_label,
        "configured_gemini_model": config.GEMINI_MODEL,
        "available_stores": [
            {"id": sid, **meta} for sid, meta in STORE_METADATA.items()
        ],
    }


@app.post("/api/analyze")
def analyze_prompt(req: AnalyzeRequest):
    """Analiza la consulta del usuario con Gemini 3.8 / LLM o reglas locales."""
    user_query = req.query.strip()
    if not user_query:
        raise HTTPException(status_code=400, detail="La consulta no puede estar vacía")

    advisor = CriteriaAdvisor()
    router = StoreRouter()

    criteria = advisor.analyze_user_prompt(user_query)
    recommendations = router.recommend_stores(criteria)

    # Preparar tiendas recomendadas
    recommended_stores = []
    for rec in recommendations:
        meta = STORE_METADATA.get(rec.store_id, {"name": rec.store_name, "color": "#64748b", "tag": ""})
        recommended_stores.append({
            "store_id": rec.store_id,
            "name": rec.store_name,
            "reason": rec.reason,
            "estimated_delivery_days": rec.estimated_delivery_days,
            "enabled_by_default": rec.enabled_by_default,
            "color": meta.get("color"),
            "tag": meta.get("tag"),
        })

    # Extraer aspectos de afinado dinámicos
    refinements = []
    for asp in criteria.refinement_aspects:
        refinements.append({
            "key": asp.key,
            "question": asp.question,
            "options": asp.options,
            "recommended_option": asp.recommended_option,
        })

    return {
        "analysis_engine": criteria.analysis_engine or "Reglas Locales Heurísticas",
        "raw_query": criteria.raw_query,
        "clean_query": criteria.clean_query,
        "category": criteria.category.value,
        "product_type": criteria.product_type,
        "product_type_label": criteria.product_type_label,
        "target_brand": criteria.target_brand,
        "target_model": criteria.target_model,
        "target_models": criteria.target_models,
        "min_price": criteria.min_price,
        "max_price": criteria.max_price,
        "min_ram_gb": criteria.min_ram_gb,
        "min_storage_gb": criteria.min_storage_gb,
        "allowed_cpus": criteria.allowed_cpus,
        "must_have_keywords": criteria.must_have_keywords,
        "exclude_keywords": criteria.exclude_keywords,
        "is_generic": criteria.is_generic,
        "refinement_aspects": refinements,
        "recommended_stores": recommended_stores,
        "all_stores": [
            {"id": sid, **meta} for sid, meta in STORE_METADATA.items()
        ],
    }


def _execute_store_search(store_id: str, criteria: SearchCriteria) -> List[ProductResult]:
    """Ejecuta la búsqueda de forma segura en un proveedor de tienda."""
    provider_cls = STORE_PROVIDER_MAP.get(store_id)
    if not provider_cls:
        return []
    provider = provider_cls()
    try:
        return provider.search(criteria)
    except Exception as e:
        logger.error(f"Error al buscar en tienda {store_id}: {e}")
        return []
    finally:
        provider.close()


@app.post("/api/search")
def search_products(req: SearchRequest):
    """Ejecuta la búsqueda multitienda concurrente y filtra con el agregador inteligente."""
    advisor = CriteriaAdvisor()
    aggregator = Aggregator()

    # Reconstruir SearchCriteria desde la petición
    category_enum = ProductCategory.GENERAL_TECH
    for pc in ProductCategory:
        if pc.value == req.category or pc.name.lower() == req.category.lower():
            category_enum = pc
            break

    models_list = list(req.target_models)
    if req.target_model and req.target_model not in models_list:
        models_list.append(req.target_model)
    target_variants = advisor.build_model_variants(models_list, req.target_brand)

    target_queries = advisor.build_targeted_queries(
        req.clean_query,
        req.allowed_cpus,
        req.min_ram_gb,
        req.min_storage_gb,
        target_model=req.target_model,
        target_models=req.target_models,
        target_brand=req.target_brand,
    )

    criteria = SearchCriteria(
        raw_query=req.raw_query or req.clean_query,
        clean_query=req.clean_query,
        category=category_enum,
        product_type=req.product_type,
        product_type_label=req.product_type_label,
        target_brand=req.target_brand,
        target_model=req.target_model,
        target_models=req.target_models,
        target_model_variants=target_variants,
        min_system_price=35.0,
        min_price=req.min_price,
        max_price=req.max_price,
        key_specs=[],
        must_have_keywords=req.must_have_keywords,
        exclude_keywords=req.exclude_keywords,
        min_ram_gb=req.min_ram_gb,
        min_storage_gb=req.min_storage_gb,
        allowed_cpus=req.allowed_cpus,
        target_search_queries=target_queries,
        ships_from_spain_only=True,
        in_stock_only=True,
    )

    # Si el usuario seleccionó refinamientos interactivos, aplicarlos
    if req.selected_refinements:
        criteria = advisor.refine_criteria(criteria, req.selected_refinements)

    # Búsqueda concurrente en las tiendas seleccionadas
    stores_to_search = [s for s in req.selected_stores if s in STORE_PROVIDER_MAP]
    if not stores_to_search:
        stores_to_search = ["aliexpress_es", "amazon_es", "pccomponentes"]

    raw_candidates: List[ProductResult] = []
    for store_id in stores_to_search:
        try:
            results = _execute_store_search(store_id, criteria)
            raw_candidates.extend(results)
        except Exception as e:
            logger.error(f"Error al consultar tienda '{store_id}': {e}")

    # Filtrar y ordenar con Aggregator
    ranked_products = aggregator.filter_and_rank(raw_candidates, criteria)
    discards = aggregator.last_discard_records
    discard_summary = aggregator.get_discard_summary()

    # Formatear productos
    products_data = []
    for p in ranked_products:
        meta = STORE_METADATA.get(
            p.store_name.lower().replace(" ", "_"),
            {"color": "#3b82f6", "tag": p.store_name}
        )
        products_data.append({
            "title": p.title,
            "price": p.price,
            "original_price": p.original_price,
            "currency": p.currency,
            "store_name": p.store_name,
            "url": p.url,
            "in_stock": p.in_stock,
            "ships_from_spain": p.ships_from_spain,
            "score": round(p.match_score, 1),
            "matched_specs": p.matched_specs,
            "image_url": p.image_url,
            "store_color": meta.get("color", "#3b82f6"),
            "store_tag": meta.get("tag", p.store_name),
        })

    # Formatear descartes
    discards_data = []
    for d in discards:
        discards_data.append({
            "store_name": d.product.store_name,
            "title": d.product.title,
            "price": d.product.price,
            "reason": d.reason.value,
            "detail": d.detail,
        })

    summary_clean = {k: v for k, v in discard_summary.items()}

    return {
        "total_raw": len(raw_candidates),
        "total_valid": len(ranked_products),
        "total_discarded": len(discards),
        "stores_queried": stores_to_search,
        "criteria_used": {
            "clean_query": criteria.clean_query,
            "min_ram_gb": criteria.min_ram_gb,
            "min_storage_gb": criteria.min_storage_gb,
            "allowed_cpus": criteria.allowed_cpus,
            "min_price": criteria.min_price,
            "max_price": criteria.max_price,
            "exclude_keywords": criteria.exclude_keywords,
        },
        "products": products_data,
        "discards": discards_data,
        "discard_summary": summary_clean,
    }


# ------------------------------------------------------------------------------
# Servir Interfaz Web
# ------------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_index():
    """Sirve la página web interactiva principal."""
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>MarketPulse Web: Plantilla index.html no encontrada</h1>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())
