from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class ProductCategory(str, Enum):
    LAPTOPS = "portatiles"
    PC_COMPONENTS = "componentes_pc"
    SMARTPHONES = "smartphones"
    MONITORS = "monitores"
    AUDIO = "audio"
    GAMING = "gaming"
    HOME_APPLIANCES = "electrodomesticos"
    GENERAL_TECH = "tecnologia_general"
    OTHER = "otros"


class SearchCriteria(BaseModel):
    raw_query: str = Field(..., description="Consulta original introducida por el usuario")
    clean_query: str = Field(..., description="Término optimizado para motores de búsqueda de tiendas")
    category: ProductCategory = Field(default=ProductCategory.GENERAL_TECH)
    min_price: Optional[float] = Field(default=None, description="Precio mínimo en euros")
    max_price: Optional[float] = Field(default=None, description="Presupuesto máximo en euros")
    key_specs: List[str] = Field(default_factory=list, description="Especificaciones clave (ej: 16GB RAM, RTX 4060, i7)")
    must_have_keywords: List[str] = Field(default_factory=list, description="Palabras indispensables en el título/descripción")
    exclude_keywords: List[str] = Field(default_factory=list, description="Palabras que descartan el resultado (ej: reacondicionado)")
    min_ram_gb: Optional[int] = Field(default=None, description="Capacidad mínima de RAM exigida en GB")
    min_storage_gb: Optional[int] = Field(default=None, description="Capacidad mínima de almacenamiento SSD exigida en GB")
    allowed_cpus: List[str] = Field(default_factory=list, description="Modelos de procesador permitidos (ej: N100, N150, I3-1215U)")
    max_price_by_cpu: Dict[str, float] = Field(default_factory=dict, description="Límites máximos de precio por procesador")
    target_search_queries: List[str] = Field(default_factory=list, description="Consultas de búsqueda complementarias segmentadas")
    target_model: Optional[str] = Field(default=None, description="Identificador o código de modelo específico (ej: EQi12, S12 Pro, NucBox G3)")
    target_model_variants: List[str] = Field(default_factory=list, description="Variantes normalizadas del token de modelo (ej: EQi12, EQi-12, EQI 12)")
    min_score_threshold: float = Field(default=80.0, description="Umbral de corte de afinidad mínima (por defecto 80%)")
    in_stock_only: bool = Field(default=True, description="Filtrar solo productos en stock")
    ships_from_spain_only: bool = Field(default=True, description="Garantizar envío desde España o almacén europeo sin aduanas")
    sort_by: str = Field(default="relevance", description="Criterio de ordenación: relevance, price_asc, price_desc")


class ProductResult(BaseModel):
    title: str = Field(..., description="Título o descripción del producto")
    price: float = Field(..., description="Precio actual en euros")
    original_price: Optional[float] = Field(default=None, description="Precio anterior si está rebajado")
    currency: str = Field(default="EUR")
    store_name: str = Field(..., description="Nombre de la tienda proveedora")
    url: str = Field(..., description="Enlace directo al artículo")
    in_stock: bool = Field(default=True, description="Disponibilidad")
    ships_from_spain: bool = Field(default=True, description="Si el envío se realiza desde España/UE")
    match_score: float = Field(default=0.0, description="Puntuación de afinidad de 0 a 100")
    matched_specs: List[str] = Field(default_factory=list, description="Especificaciones encontradas que coinciden con los criterios")
    image_url: Optional[str] = Field(default=None, description="Miniatura del producto")

    @property
    def discount_percentage(self) -> Optional[float]:
        if self.original_price and self.original_price > self.price:
            return round(((self.original_price - self.price) / self.original_price) * 100, 1)
        return None


class StoreRecommendation(BaseModel):
    store_id: str
    store_name: str
    reason: str
    priority: int = Field(default=1, description="1 es máxima prioridad")
    shipping_info: str
    estimated_delivery_days: str
    enabled_by_default: bool = True
