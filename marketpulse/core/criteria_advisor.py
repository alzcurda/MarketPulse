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
            "mini pc", "minipc", "barebone", "sobremesa", "ordenador",
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
        Extrae rangos de presupuesto monetario (requiere símbolo € o palabra euros o contexto de precio).
        Evita confundir especificaciones técnicas como '16 GB de RAM' con precios.
        """
        text_lower = text.lower().replace(",", ".")
        min_price = None
        max_price = None

        # Descartar falsos positivos donde un número precede a unidades de hardware
        def is_valid_price(number_str: str, full_match_end: int, raw_text: str) -> bool:
            sub = raw_text[full_match_end:].strip().lower()
            if re.match(r"^(?:gb|tb|hz|ram|rom|ssd|disco|pulgadas|dias|días|anos|años)", sub):
                return False
            return True

        # 1. Patrón: entre X y Y euros/€
        between_match = re.search(r"entre\s+(\d+(?:\.\d+)?)\s*(?:€|euros)?\s*y\s*(\d+(?:\.\d+)?)\s*(?:€|euros)", text_lower)
        if between_match:
            min_price = float(between_match.group(1))
            max_price = float(between_match.group(2))
            return min_price, max_price

        # 2. Patrón: menos de X, maximo X, hasta X
        for m in re.finditer(r"(?:menos de|hasta|máximo|maximo|presupuesto de|por debajo de)\s*(\d+(?:\.\d+)?)\s*(?:€|euros)?", text_lower):
            if is_valid_price(m.group(1), m.end(), text_lower):
                # Si no tiene € explícito, verificar que no sea un spec de hardware
                if "€" in m.group(0) or "euro" in m.group(0) or "presupuesto" in m.group(0):
                    max_price = float(m.group(1))
                elif float(m.group(1)) >= 50: # Los precios reales en esta categoría suelen ser >= 50
                    max_price = float(m.group(1))

        # 3. Patrón: mas de X, minimo X, a partir de X
        for m in re.finditer(r"(?:más de|mas de|mínimo|minimo|a partir de|desde)\s*(\d+(?:\.\d+)?)\s*(?:€|euros)", text_lower):
            if is_valid_price(m.group(1), m.end(), text_lower):
                min_price = float(m.group(1))

        return min_price, max_price

    def extract_conditional_prices(self, text: str) -> Dict[str, float]:
        """
        Detecta precios condicionales por CPU como:
        'precio máximo de 230 € para N100/N150 y hasta 330 € para los Core i3'
        """
        prices: Dict[str, float] = {}

        pat = r"(?:precio máximo de|precio maximo de|hasta|máximo de?|maximo de?)\s*(\d+(?:\.\d+)?)\s*€?\s*(?:para|en)\s*([^\.,]+?)(?=\s+(?:y|e)\s+|\.|\,|$)"

        for m in re.finditer(pat, text, flags=re.I):
            try:
                price_val = float(m.group(1))
                target_str = m.group(2).upper()
                if "N100" in target_str:
                    prices["N100"] = price_val
                if "N150" in target_str:
                    prices["N150"] = price_val
                if "N95" in target_str:
                    prices["N95"] = price_val
                if "N305" in target_str:
                    prices["N305"] = price_val
                if "I3" in target_str:
                    prices["I3"] = price_val
                if "I5" in target_str:
                    prices["I5"] = price_val
            except ValueError:
                pass

        return prices

    def extract_key_specs(self, text: str) -> List[str]:
        """Detecta especificaciones técnicas positivas mencionadas en la consulta."""
        found_specs = []
        text_upper = text.upper()

        # Detección de memoria RAM
        ram_match = re.findall(r"\b(\d{1,2}\s*GB)\b", text_upper)
        for ram in ram_match:
            spec = f"{ram.replace(' ', '')} RAM"
            if spec not in found_specs:
                found_specs.append(spec)

        # Detección de procesadores o gráficas habituales
        patterns = [
            r"\b(RTX\s*\d{4}(?:\s*TI)?)\b",
            r"\b(GTX\s*\d{4})\b",
            r"\b(RYZEN\s*\d(?:\s*\d{4}[A-Z]*)?)\b",
            r"\b(I[3579]-(?:1[2-4]\d{2}[A-Z]*|N\d{3}))\b",
            r"\b(I[3579]-?\d{4,5}[A-Z]*)\b",
            r"\b(I[3579])\b",
            r"\b(INTEL\s*N\d{2,3})\b",
            r"\b(N\d{2,3})\b",
            r"\b(I3-N305|N305)\b",
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

    def extract_allowed_cpus(self, text: str) -> List[str]:
        """Detecta modelos específicos de CPU requeridos por el usuario, preservando el orden de mención."""
        text_upper = text.upper()
        found = []

        patterns = [
            r"\b(I[3579]-(?:1[2-4]\d{2}[A-Z]*|N\d{3}))\b",
            r"\b(I3-N305)\b",
            r"\b(N305)\b",
            r"\b(N\d{2,3})\b",
        ]

        for pat in patterns:
            for m in re.finditer(pat, text_upper):
                val = m.group(1).strip()
                found.append((m.start(), val))

        found.sort(key=lambda x: x[0])
        allowed = []
        for _, val in found:
            if val == "N305" and "I3-N305" in allowed:
                continue
            if val not in allowed:
                allowed.append(val)

        return allowed

    @staticmethod
    def generate_model_variants(raw_model: str) -> List[str]:
        """Genera variantes normalizadas de un código de modelo (ej: EQi12, EQi-12, EQI 12)."""
        norm = raw_model.lower().strip()
        clean = re.sub(r"[^a-z0-9]", "", norm)
        variants = {norm, clean}

        # Separar letras y números con guion y espacio (ej. eqi12 -> eqi-12, eqi 12)
        m = re.match(r"^([a-z]+)(\d+.*)$", clean)
        if m:
            variants.add(f"{m.group(1)}-{m.group(2)}")
            variants.add(f"{m.group(1)} {m.group(2)}")

        if " " in norm:
            variants.add(norm.replace(" ", "-"))
            variants.add(norm.replace(" ", ""))
        if "-" in norm:
            variants.add(norm.replace("-", " "))
            variants.add(norm.replace("-", ""))

        return sorted(list(variants))

    def extract_target_model(self, text: str) -> Tuple[Optional[str], List[str]]:
        """
        Detecta identificadores o códigos de modelo específicos solicitados por el usuario
        (ej: EQi12, S12 Pro, NucBox G3, MP100 Pro, SER5, Cubi 5) y genera sus variantes normalizadas.
        """
        exclusion_split = re.split(
            r"\b(?:descartando|excluyendo|evitando|sin\s+(?:procesador|equipos?|marcas?|amd|celeron)|no\s+quiero|nada\s+de)\b",
            text,
            flags=re.I,
        )
        text_positive = exclusion_split[0]

        known_non_models = {
            "n100", "n150", "n95", "n5095", "n5105", "n2940", "n2840", "j4125", "j3355",
            "16gb", "32gb", "64gb", "8gb", "4gb", "12gb", "512gb", "256gb", "128gb", "1tb", "2tb",
            "windows", "win11", "win10", "ddr4", "ddr5", "wifi", "bluetooth", "hdmi", "usb",
            "intel", "amd", "ryzen", "core", "celeron", "pentium", "geforce", "radeon",
            "portatil", "laptop", "sobremesa", "ordenador", "pc", "mini", "minipc", "desktop"
        }

        model_patterns = [
            r"\b(NucBox\s*[A-Z0-9]+)\b",
            r"\b(Mini\s*S(?:12)?(?:\s*Pro)?)\b",
            r"\b(S12\s*Pro)\b",
            r"\b(EQi-?\s*\d{1,2}(?:\s*Pro)?)\b",
            r"\b(EQ-?\s*\d{1,2}(?:\s*Pro)?)\b",
            r"\b(SE[iR]-?\s*\d{1,2}(?:\s*Pro|\s*Max)?)\b",
            r"\b(MP\d{2,3}(?:\s*Pro)?)\b",
            r"\b(Cubi\s*\d{1,2}[A-Za-z0-9-]*)\b",
            r"\b([A-Z]{1,3}\d{1,3}\s*(?:Pro|Plus|Max|Ultra|Air)?)\b",
        ]

        for pat in model_patterns:
            for m in re.finditer(pat, text_positive, flags=re.I):
                raw_model = m.group(1).strip()
                norm_check = raw_model.lower().replace(" ", "").replace("-", "")
                if norm_check in known_non_models or re.match(r"^i[3579]$", norm_check):
                    continue
                if re.match(r"^(?:n\d{2,3}|16gb|512gb|1tb)$", norm_check):
                    continue
                if len(norm_check) < 3:
                    continue

                variants = self.generate_model_variants(raw_model)
                return raw_model, variants

        return None, []

    def extract_hardware_limits(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extrae requisitos mínimos de RAM (GB) y almacenamiento SSD (GB)."""
        text_lower = text.lower()
        min_ram = None
        min_storage = None

        # Requisito mínimo de RAM
        m_ram = re.search(r"(?:como mínimo|mínimo|al menos|desde)\s*(\d{1,2})\s*gb\s*(?:de\s*)?ram", text_lower)
        if not m_ram:
            m_ram = re.search(r"(\d{1,2})\s*gb\s*(?:de\s*)?ram\s*(?:como mínimo|mínimo|o más)", text_lower)
        if m_ram:
            min_ram = int(m_ram.group(1))

        # Requisito mínimo de almacenamiento SSD
        m_storage = re.search(r"(?:como mínimo|mínimo|al menos|desde)\s*(\d{3,4})\s*gb(?:\s*o\s*(\d)\s*tb)?\s*(?:de\s*)?(?:ssd|disco|almacenamiento)", text_lower)
        if m_storage:
            min_storage = int(m_storage.group(1))
        else:
            m_tb = re.search(r"(?:como mínimo|mínimo|al menos)\s*(\d)\s*tb", text_lower)
            if m_tb:
                min_storage = int(m_tb.group(1)) * 1024

        return min_ram, min_storage

    def extract_exclusions(self, text: str) -> List[str]:
        """Extrae palabras y marcas explícitamente excluidas."""
        text_lower = text.lower()
        exclude_list = []

        # Marcas y arquitecturas
        if re.search(r"\bamd\b", text_lower):
            exclude_list.extend(["amd", "ryzen"])
        if re.search(r"\bryzen\b", text_lower) and "ryzen" not in exclude_list:
            exclude_list.append("ryzen")
        if re.search(r"\bceleron\b", text_lower):
            exclude_list.append("celeron")
        if re.search(r"\bpentium\b", text_lower):
            exclude_list.append("pentium")

        # Chips específicos antiguos
        for m in re.finditer(r"\b([jn]\d{4})\b", text_lower):
            chip = m.group(1)
            if chip not in exclude_list:
                exclude_list.append(chip)

        # Configuraciones de RAM y disco descartadas
        if re.search(r"\b8\s*gb\b", text_lower):
            exclude_list.append("8gb")
        if re.search(r"\b256\s*gb\b", text_lower):
            exclude_list.append("256gb")
        if re.search(r"\b128\s*gb\b", text_lower):
            exclude_list.append("128gb")

        # Procedencias no deseadas
        if "amazon us" in text_lower or "estados unidos" in text_lower:
            exclude_list.append("amazon us")
        if "fuera de la ue" in text_lower or "importacion" in text_lower:
            exclude_list.append("importación")

        return exclude_list

    @staticmethod
    def strip_accents(text: str) -> str:
        """Elimina tildes y caracteres diacríticos para búsquedas normalizadas."""
        nfkd_form = unicodedata.normalize('NFKD', text)
        return "".join([c for c in nfkd_form if not unicodedata.combining(c)])

    def clean_search_query(self, raw_query: str, category: ProductCategory) -> str:
        """Limpia la consulta dejando únicamente los términos clave positivos de búsqueda."""
        # 1. Eliminar cláusulas de exclusión
        exclusion_split = re.split(r"\b(?:descartando|excluyendo|evitando|sin\s+(?:procesador|equipos?|marcas?|amd|celeron)|no\s+quiero|nada\s+de)\b", raw_query, flags=re.I)
        text_to_clean = exclusion_split[0]

        # 2. Eliminar referencias de precio de la query de texto
        text_no_price = re.sub(r"(?:precio máximo de|hasta|máximo|presupuesto de?|menos de)\s*\d+[\.,]?\d*\s*€?", "", text_to_clean, flags=re.I)
        text_no_price = re.sub(r"\d+[\.,]?\d*\s*(?:€|euros)", "", text_no_price, flags=re.I)

        # Normalizar acentos y caracteres
        text_normalized = unicodedata.normalize('NFKD', text_no_price).encode('ASCII', 'ignore').decode('utf-8')
        text_clean = re.sub(r"[^\w\s-]", " ", text_clean_str := text_normalized.lower())

        filler_words = {
            "hola", "busco", "necesito", "quiero", "comprar", "encontrar", "dime", "para", "con",
            "bueno", "bonito", "barato", "calidad", "precio", "euros", "euro", "presupuesto",
            "un", "una", "unos", "unas", "el", "la", "los", "las", "de", "en", "por", "que",
            "tenga", "tengan", "minimo", "como", "al", "menos", "desde", "hasta", "envio",
            "nacional", "espana", "union", "europea", "ue", "cueste", "cuesta"
        }

        words = text_clean.split()
        filtered_words = [
            w for w in words
            if w not in filler_words and len(w) > 1 and not (w.isdigit() and len(w) <= 2)
        ]

        result = " ".join(filtered_words).strip()
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

    def build_targeted_queries(
        self,
        clean_query: str,
        allowed_cpus: List[str],
        min_ram_gb: Optional[int],
        min_storage_gb: Optional[int],
        target_model: Optional[str] = None
    ) -> List[str]:
        """
        Construye consultas segmentadas de alta precisión para los buscadores de las tiendas.
        """
        base_product = "mini pc" if "mini pc" in clean_query.lower() else clean_query.split()[0]
        ram_str = f"{min_ram_gb}gb" if min_ram_gb else ""
        storage_str = f"{min_storage_gb}gb" if min_storage_gb else ""

        queries = []
        if target_model:
            model_clean = target_model.lower()
            queries.append(f"{base_product} {model_clean}")
            if ram_str:
                queries.append(f"{base_product} {model_clean} {ram_str}")
            queries.append(model_clean)

        if allowed_cpus:
            for cpu in allowed_cpus[:6]:
                q_parts = [base_product, cpu.lower()]
                if ram_str:
                    q_parts.append(ram_str)
                if storage_str and min_storage_gb and min_storage_gb >= 512:
                    q_parts.append(storage_str)
                q_str = " ".join(q_parts)
                if q_str not in queries:
                    queries.append(q_str)
        elif not queries:
            queries.append(clean_query)

        return queries

    def analyze_user_prompt(self, prompt: str) -> SearchCriteria:
        """Analiza integralmente la entrada del usuario y genera un SearchCriteria estructurado."""
        # 1. Separar requerimientos positivos de cláusulas de exclusión
        exclusion_markers = r"\b(?:descartando|excluyendo|evitando|sin\s+(?:procesador|equipos?|marcas?|amd|celeron)|no\s+quiero|nada\s+de|quitar|obviar)\b"
        parts = re.split(exclusion_markers, prompt, flags=re.I)
        positive_text = parts[0]
        negative_text = " ".join(parts[1:]) if len(parts) > 1 else ""

        category = self.detect_category(positive_text)
        min_price, max_price = self.extract_budget(prompt)
        max_price_by_cpu = self.extract_conditional_prices(prompt)

        # Si hay precios condicionales, asegurar que max_price sea el techo superior
        if max_price_by_cpu and (max_price is None or max(max_price_by_cpu.values()) > max_price):
            max_price = max(max_price_by_cpu.values())

        # Extraer modelo específico si el usuario lo solicita
        target_model, target_model_variants = self.extract_target_model(positive_text)

        # Extraer CPUs permitidas y límites de hardware
        allowed_cpus = self.extract_allowed_cpus(positive_text)
        min_ram_gb, min_storage_gb = self.extract_hardware_limits(positive_text)

        # Especificaciones clave SOLO de la parte positiva
        key_specs = self.extract_key_specs(positive_text)

        # Exclusiones SOLO de la parte negativa
        exclude_keywords = self.extract_exclusions(negative_text)

        # Query limpia positiva para motores de búsqueda
        clean_query = self.clean_search_query(prompt, category)

        # Consultas dirigidas segmentadas
        target_queries = self.build_targeted_queries(
            clean_query, allowed_cpus, min_ram_gb, min_storage_gb, target_model=target_model
        )

        return SearchCriteria(
            raw_query=prompt,
            clean_query=clean_query,
            category=category,
            min_price=min_price,
            max_price=max_price,
            key_specs=key_specs,
            must_have_keywords=[],
            exclude_keywords=exclude_keywords,
            min_ram_gb=min_ram_gb,
            min_storage_gb=min_storage_gb,
            allowed_cpus=allowed_cpus,
            max_price_by_cpu=max_price_by_cpu,
            target_search_queries=target_queries,
            target_model=target_model,
            target_model_variants=target_model_variants,
            min_score_threshold=80.0,
            ships_from_spain_only=True,
            in_stock_only=True,
        )

    def get_suggested_specs(self, category: ProductCategory) -> List[str]:
        """Devuelve consejos y especificaciones clave a tener en cuenta según categoría."""
        return self.SUGGESTED_SPECS_BY_CATEGORY.get(category, [
            "Verificar garantía oficial de 3 años en España",
            "Comprobar disponibilidad y costes de envío"
        ])

