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


class DiscardReason(str, Enum):
    DUPLICATE_URL = "URL duplicada"
    SEARCH_PAGE_OR_PLACEHOLDER = "Página de búsqueda / enlace no válido"
    CATEGORY_MISMATCH = "Categoría ajena (electrodomésticos/no-IT)"
    ACCESSORY = "Accesorio (funda, dock, soporte, cable)"
    UNREASONABLE_PRICE = "Precio no sensato para hardware de gama alta"
    TARGET_MODEL_MISMATCH = "No coincide con el modelo objetivo"
    EXCLUDED_KEYWORD = "Contiene palabra excluida"
    OLD_INTEL_CORE = "CPU Intel Core antigua (<= 11ª gen)"
    DISALLOWED_CPU = "Procesador no permitido"
    INSUFFICIENT_RAM = "Memoria RAM insuficiente"
    INSUFFICIENT_STORAGE = "Almacenamiento SSD insuficiente"
    UNKNOWN_PRICE_WITH_BUDGET = "Precio no disponible con presupuesto fijado"
    CPU_MAX_PRICE_EXCEEDED = "Precio excede el límite fijado para este procesador"
    OUT_OF_STOCK = "Sin stock disponible"
    NON_LOCAL_SHIPPING = "Envío no nacional o aduanas"
    PRICE_ABOVE_MAX = "Precio superior al presupuesto máximo"
    PRICE_BELOW_MIN = "Precio inferior al mínimo establecido"
    AFFINITY_THRESHOLD = "Afinidad inferior al umbral mínimo requerido"
    BRAND_MISMATCH = "Marca no coincide con la solicitada"
    COMPONENT_OR_SPARE_PART = "Componente o repuesto en lugar de equipo completo"
    PRODUCT_TYPE_MISMATCH = "Tipo de artículo incompatible con el solicitado"




class RefinementAspect(BaseModel):
    key: str = Field(..., description="Identificador del parámetro (ej: ram, storage, power, grinder)")
    question: str = Field(..., description="Pregunta concisa para el usuario")
    options: List[str] = Field(default_factory=list, description="Opciones posibles de configuración")
    recommended_option: Optional[str] = Field(default=None, description="Opción recomendada por defecto")


class SearchCriteria(BaseModel):
    raw_query: str = Field(..., description="Consulta original introducida por el usuario")
    clean_query: str = Field(..., description="Término optimizado para motores de búsqueda de tiendas")
    category: ProductCategory = Field(default=ProductCategory.GENERAL_TECH)
    product_type: Optional[str] = Field(default=None, description="Tipo específico de producto (ej: mini_pc, laptop, gpu, monitor)")
    product_type_label: Optional[str] = Field(default=None, description="Etiqueta legible del tipo de producto")
    target_brand: Optional[str] = Field(default=None, description="Marca específica solicitada (ej: Trigkey, GMKtec, Apple)")
    target_series: Optional[str] = Field(default=None, description="Serie o familia de producto (ej: Green G4, NucBox, ThinkPad)")
    min_system_price: Optional[float] = Field(default=35.0, description="Precio mínimo de sensatez para equipos informáticos completos")
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
    target_models: List[str] = Field(default_factory=list, description="Lista de modelos específicos permitidos cuando hay múltiples opciones")
    target_model_variants: List[str] = Field(default_factory=list, description="Variantes normalizadas del token de modelo (ej: EQi12, EQi-12, EQI 12)")
    min_score_threshold: float = Field(default=80.0, description="Umbral de corte de afinidad mínima (por defecto 80%)")
    in_stock_only: bool = Field(default=True, description="Filtrar solo productos en stock")
    ships_from_spain_only: bool = Field(default=True, description="Garantizar envío desde España o almacén europeo sin aduanas")
    sort_by: str = Field(default="relevance", description="Criterio de ordenación: relevance, price_asc, price_desc")
    is_generic: bool = Field(default=False, description="Indica si la búsqueda representa un concepto amplio con múltiples configuraciones")
    refinement_aspects: List[RefinementAspect] = Field(default_factory=list, description="Preguntas dinámicas de afinado sugeridas por el asesor")
    analysis_engine: Optional[str] = Field(default=None, description="Motor semántico utilizado para el análisis (Ollama, Gemini, Reglas Locales, etc.)")


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


class DiscardRecord(BaseModel):
    product: ProductResult
    reason: DiscardReason
    detail: str


class StoreRecommendation(BaseModel):
    store_id: str
    store_name: str
    reason: str
    priority: int = Field(default=1, description="1 es máxima prioridad")
    shipping_info: str
    estimated_delivery_days: str
    enabled_by_default: bool = True
