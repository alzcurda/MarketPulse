import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from marketpulse.models import ProductCategory, SearchCriteria


class CriteriaAdvisor:
    """
    Módulo de asesoramiento que analiza la petición del usuario en lenguaje natural,
    detecta la categoría, extrae límites de presupuesto y traduce una descripción
    conversacional en una consulta limpia y un conjunto de especificaciones técnicas clave.
    """

    # Diccionario de palabras clave por categoría
    CATEGORY_KEYWORDS: Dict[ProductCategory, List[str]] = {
        ProductCategory.LAPTOPS: [
            "portatil", "portátil", "laptop", "notebook", "macbook", "ultrabook", "thinkpad"
        ],
        ProductCategory.PC_COMPONENTS: [
            "tarjeta grafica", "gráfica", "gpu", "procesador", "cpu", "placa base", "motherboard",
            "memoria ram", "disco duro", "ssd", "fuente de alimentacion", "caja pc", "refrigeracion"
        ],
        ProductCategory.MONITORS: [
            "monitor", "pantalla", "display", "hz", "oled", "ips", "curvo"
        ],
        ProductCategory.SMARTPHONES: [
            "smartphone", "movil", "móvil", "telefono", "teléfono", "iphone", "xiaomi", "samsung galaxy"
        ],
        ProductCategory.AUDIO: [
            "auriculares", "altavoz", "altavoces", "headphones", "soundbar", "barra de sonido", "microfono"
        ],
        ProductCategory.GAMING: [
            "consola", "playstation", "ps5", "xbox", "nintendo switch", "mando", "gamepad", "silla gaming"
        ],
        ProductCategory.HOME_APPLIANCES: [
            "aspiradora", "cafetera", "freidora", "airfryer", "robot aspirador", "microondas"
        ],
    }

    # Recomendaciones sugeridas por categoría para orientar al comprador
    SUGGESTED_SPECS_BY_CATEGORY: Dict[ProductCategory, List[str]] = {
        ProductCategory.LAPTOPS: [
            "16GB RAM mínimo (recomendado para multitarea y desarrollo)",
            "SSD 512GB o 1TB NVMe",
            "Procesador Intel Core i5/i7 o AMD Ryzen 5/7 de última generación",
            "Pantalla IPS Full HD o superior"
        ],
        ProductCategory.PC_COMPONENTS: [
            "Compatibilidad de socket / chipset",
            "VRAM (8GB+ para gaming moderno)",
            "Potencia de fuente (certificación 80 Plus Gold)",
        ],
        ProductCategory.MONITORS: [
            "Tasa de refresco (144Hz+ para gaming, 60-75Hz oficina)",
            "Panel IPS (mejores ángulos de visión y colores)",
            "Resolución (QHD 2K recomendado a partir de 27 pulgadas)",
        ],
        ProductCategory.SMARTPHONES: [
            "Conectividad 5G",
            "Almacenamiento (128GB o 256GB mínimo)",
            "Pantalla AMOLED / 120Hz",
            "Carga rápida y soporte de actualizaciones",
        ],
        ProductCategory.AUDIO: [
            "Cancelación Activa de Ruido (ANC)",
            "Autonomía (30h+ en diadema o 6h+ en estuche TWS)",
            "Códecs de alta fidelidad (LDAC, aptX)",
        ]
    }

    def detect_category(self, text: str) -> ProductCategory:
        """Identifica la categoría más probable a partir del texto."""
        text_lower = text.lower()
        for cat, keywords in self.CATEGORY_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                return cat
        return ProductCategory.GENERAL_TECH

    def extract_budget(self, text: str) -> Tuple[Optional[float], Optional[float]]:
        """
        Extrae rangos de presupuesto como 'menos de 800€', 'hasta 1000', 'entre 500 y 700€'.
        """
        text_lower = text.lower().replace(",", ".")
        min_price = None
        max_price = None

        # Patrón: entre X y Y
        between_match = re.search(r"entre\s+(\d+(?:\.\d+)?)\s*(?:€|euros)?\s*y\s*(\d+(?:\.\d+)?)\s*(?:€|euros)?", text_lower)
        if between_match:
            min_price = float(between_match.group(1))
            max_price = float(between_match.group(2))
            return min_price, max_price

        # Patrón: menos de X, maximo X, hasta X
        max_match = re.search(r"(?:menos de|hasta|máximo|maximo|presupuesto de|por debajo de)\s*(\d+(?:\.\d+)?)\s*(?:€|euros)?", text_lower)
        if max_match:
            max_price = float(max_match.group(1))

        # Patrón: mas de X, minimo X, a partir de X
        min_match = re.search(r"(?:más de|mas de|mínimo|minimo|a partir de)\s*(\d+(?:\.\d+)?)\s*(?:€|euros)?", text_lower)
        if min_match:
            min_price = float(min_match.group(1))

        return min_price, max_price

    def extract_key_specs(self, text: str) -> List[str]:
        """Detecta especificaciones técnicas mencionadas en la consulta."""
        found_specs = []
        text_upper = text.upper()

        # Detección de memoria RAM
        ram_match = re.findall(r"\b(\d{1,2}\s*GB)\b", text_upper)
        for ram in ram_match:
            found_specs.append(f"{ram.replace(' ', '')} RAM")

        # Detección de procesadores o gráficas habituales
        patterns = [
            r"\b(RTX\s*\d{4}(?:\s*TI)?)\b",
            r"\b(GTX\s*\d{4})\b",
            r"\b(RYZEN\s*\d)\b",
            r"\b(I[3579]-?\d{4,5}[A-Z]*)\b",
            r"\b(I[3579])\b",
            r"\b(OLED|AMOLED|IPS)\b",
            r"\b(\d{2,3}\s*HZ)\b",
            r"\b(1TB|512GB|256GB|2TB)\s*(?:SSD)?\b",
        ]

        for pat in patterns:
            matches = re.findall(pat, text_upper)
            for m in matches:
                clean_spec = m.replace("  ", " ").strip()
                if clean_spec not in found_specs:
                    found_specs.append(clean_spec)

        return found_specs

    @staticmethod
    def strip_accents(text: str) -> str:
        """Elimina tildes y caracteres diacríticos para búsquedas normalizadas."""
        nfkd_form = unicodedata.normalize('NFKD', text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def clean_search_query(self, text: str, category: ProductCategory) -> str:
        """
        Convierte una petición conversacional (ej. 'quiero un portátil para programar que tenga 16gb')
        en una query compacta y efectiva para buscadores de tiendas (ej. 'portatil 16gb').
        """
        # Normalizar tildes para evitar discrepancias de codificación o formato
        text_normalized = self.strip_accents(text.lower())

        # Eliminar palabras de relleno coloquial (sin tildes)
        filler_words = [
            "hola", "quiero", "busco", "necesito", "un", "una", "unos", "unas", "para", "que", "tenga",
            "sea", "bueno", "bonito", "barato", "comprar", "encontrar", "sobre", "alrededor", "de",
            "euros", "euro", "por favor", "me gustaria", "estoy buscando", "trabajar", "programar"
        ]

        cleaned = text_normalized
        # Quitar rangos de precio del texto de búsqueda para no contaminar el buscador de la tienda
        cleaned = re.sub(r"(?:menos de|hasta|maximo|entre|a partir de|minimo)\s*\d+.*?(?:€|euros)?", "", cleaned)
        cleaned = re.sub(r"\d+\s*(?:€|euros)", "", cleaned)

        # Tokenizar y filtrar
        words = re.findall(r"[a-zA-Z0-9]+", cleaned)
        filtered_words = [w for w in words if w not in filler_words and len(w) > 1]

        result = " ".join(filtered_words).strip()
        # Si quedó vacío o muy corto, asegurar al menos la palabra clave de categoría
        if not result:
            if category == ProductCategory.LAPTOPS:
                result = "portatil"
            elif category == ProductCategory.SMARTPHONES:
                result = "smartphone"
            elif category == ProductCategory.MONITORS:
                result = "monitor"
            else:
                result = text_normalized.strip()

        return result

    def analyze_user_prompt(self, prompt: str) -> SearchCriteria:
        """Analiza integralmente la entrada del usuario y genera un SearchCriteria estructurado."""
        category = self.detect_category(prompt)
        min_price, max_price = self.extract_budget(prompt)
        key_specs = self.extract_key_specs(prompt)
        clean_query = self.clean_search_query(prompt, category)

        return SearchCriteria(
            raw_query=prompt,
            clean_query=clean_query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            key_specs=key_specs,
            ships_from_spain_only=True,
            in_stock_only=True,
        )

    def get_suggested_specs(self, category: ProductCategory) -> List[str]:
        """Devuelve consejos y especificaciones clave a tener en cuenta según categoría."""
        return self.SUGGESTED_SPECS_BY_CATEGORY.get(category, [
            "Verificar garantía oficial de 3 años en España",
            "Comprobar disponibilidad y costes de envío"
        ])
