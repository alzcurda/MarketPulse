import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple
from marketpulse.models import ProductCategory, RefinementAspect, SearchCriteria
from marketpulse.core.llm_client import LLMClient


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

    KNOWN_BRANDS: List[str] = [
        "trigkey", "gmktec", "beelink", "minisforum", "geekom", "chuwi", "nippo", "acemagic", "bmax", "blackview",
        "ouvis", "kamrui", "mllse", "soyo", "firebat", "genmachine", "topton", "mele", "chatreey", "morefine", "szbox",
        "apple", "hp", "lenovo", "dell", "asus", "acer", "msi", "samsung", "xiaomi", "gigabyte",
        "sony", "lg", "huawei", "toshiba", "motorola", "oppo", "realme", "google", "bose", "sennheiser"
    ]

    PRODUCT_TYPES = [
        ("mini_pc", "Mini PC / Ordenador de sobremesa compacto", [r"\bmini\s*pc\b", r"\bminipc\b", r"\bbarebone\b", r"\bmicro\s*pc\b"]),
        ("laptop", "Portátil / Laptop", [r"\bport[aá]til\b", r"\blaptop\b", r"\bnotebook\b", r"\bmacbook\b", r"\bultrabook\b"]),
        ("desktop", "Ordenador de Sobremesa / Torre", [r"\bsobremesa\b", r"\btorre\s*pc\b", r"\bordenador\s*gaming\b", r"\bpc\s*gaming\b", r"\bordenador\s*de\s*sobremesa\b"]),
        ("gpu", "Tarjeta Gráfica (GPU)", [r"\btarjeta\s*gr[aá]fica\b", r"\bgr[aá]fica\b", r"\bgpu\b", r"\brtx\s*\d{4}\b", r"\brx\s*\d{4}\b"]),
        ("cpu", "Procesador (CPU)", [r"\bprocesador\b", r"\bcpu\b", r"\bryzen\s*\d\b", r"\bintel\s*core\b"]),
        ("ram", "Memoria RAM", [r"\bmemoria\s*ram\b", r"\bddr[45]\b"]),
        ("storage", "Disco Duro / SSD", [r"\bdisco\s*duro\b", r"\bssd\b", r"\bnvme\b", r"\bm\.2\b"]),
        ("monitor", "Monitor / Pantalla", [r"\bmonitor\b", r"\bpantalla\b", r"\bdisplay\b"]),
        ("smartphone", "Teléfono Móvil / Smartphone", [r"\bsmartphone\b", r"\bm[oó]vil\b", r"\btel[eé]fono\b", r"\biphone\b"]),
        ("audio", "Auriculares / Dispositivo de Audio", [r"\bauriculares\b", r"\baltavoz\b", r"\baltavoces\b", r"\bheadphones\b", r"\bsoundbar\b"]),
    ]

    def detect_brand(self, text: str) -> Optional[str]:
        """Detecta marcas comerciales reconocidas en la petición."""
        text_lower = text.lower()
        for brand in self.KNOWN_BRANDS:
            if re.search(rf"\b{re.escape(brand)}\b", text_lower):
                return brand.title()
        return None

    def detect_product_type(self, text: str, category: ProductCategory) -> Tuple[str, str]:
        """Detecta la tipología específica de artículo buscado y su etiqueta legible."""
        text_lower = text.lower()
        for p_type, label, patterns in self.PRODUCT_TYPES:
            if any(re.search(pat, text_lower) for pat in patterns):
                return p_type, label
        if category == ProductCategory.LAPTOPS:
            return "laptop", "Portátil / Laptop"
        elif category == ProductCategory.MONITORS:
            return "monitor", "Monitor / Pantalla"
        elif category == ProductCategory.SMARTPHONES:
            return "smartphone", "Teléfono Móvil / Smartphone"
        elif category == ProductCategory.AUDIO:
            return "audio", "Auriculares / Dispositivo de Audio"
        return "tecnologia_general", "Dispositivo tecnológico"

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
        """Genera variantes normalizadas de un código de modelo (ej: EQi12, EQi-12, EQI 12, Mini S12 Pro)."""
        norm = raw_model.lower().strip()
        clean = re.sub(r"[^a-z0-9]", "", norm)
        variants = {norm, clean}

        # Separar letras y números con guion y espacio (ej. eqi12 -> eqi-12, eqi 12)
        m = re.match(r"^([a-z]+)(\d+.*)$", clean)
        if m:
            variants.add(f"{m.group(1)}-{m.group(2)}")
            variants.add(f"{m.group(1)} {m.group(2)}")

        # Patrón letra + número + letras (ej. s12pro -> s 12 pro, s-12-pro, s12 pro)
        m_full = re.match(r"^([a-z]+?)(\d+)([a-z]+)$", clean)
        if m_full:
            prefix, num, suffix = m_full.groups()
            variants.add(f"{prefix}{num} {suffix}")
            variants.add(f"{prefix} {num} {suffix}")
            variants.add(f"{prefix}-{num}-{suffix}")
            variants.add(f"{prefix}{num}-{suffix}")

        if " " in norm:
            variants.add(norm.replace(" ", "-"))
            variants.add(norm.replace(" ", ""))
            # Separar letras de números en cada subpalabra (ej: mini s12 pro -> mini s 12 pro)
            expanded_words = []
            for w in norm.split():
                mw = re.match(r"^([a-z]+)(\d+)$", w)
                if mw:
                    expanded_words.append(f"{mw.group(1)} {mw.group(2)}")
                else:
                    expanded_words.append(w)
            variants.add(" ".join(expanded_words))

        if "-" in norm:
            variants.add(norm.replace("-", " "))
            variants.add(norm.replace("-", ""))

        return sorted(list(variants))

    def extract_target_models(self, text: str) -> Tuple[Optional[str], List[str], List[str]]:
        """
        Detecta uno o varios modelos específicos solicitados por el usuario
        (ej: NucBox G3, G5, M5 o M6; Beelink SER5 o S12 Pro) y genera todas sus variantes.
        Devuelve: (modelo_principal, lista_modelos, lista_variantes)
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
            "portatil", "laptop", "sobremesa", "ordenador", "pc", "mini", "minipc", "desktop",
            "modelos", "modelo"
        }

        # Detectar marca si está presente
        brand = self.detect_brand(text_positive)
        brand_norm = brand.lower() if brand else None

        target_models: List[str] = []

        # 1. Detectar listas de series (ej: "Green G4", "Speed S5", "NucBox G3, G5, M5 o M6", "SER5", etc.)
        series_match = re.search(
            r"\b(Green|Speed|NucBox|Mini\s*S|EQi|EQ|SER|SEi|MP|Cubi|ProDesk|EliteDesk|ThinkCentre)\s+([A-Za-z0-9\s,oy]+)",
            text_positive,
            re.I
        )
        canonical_series = {
            "green": "Green",
            "speed": "Speed",
            "nucbox": "NucBox",
            "mini s": "Mini S",
            "eqi": "EQi",
            "eq": "EQ",
            "ser": "SER",
            "sei": "SEi",
            "mp": "MP",
            "cubi": "Cubi",
            "prodesk": "ProDesk",
            "elitedesk": "EliteDesk",
            "thinkcentre": "ThinkCentre",
        }
        if series_match:
            prefix_raw = series_match.group(1).strip()
            prefix = canonical_series.get(prefix_raw.lower(), prefix_raw)
            tail = series_match.group(2)
            # Extraer tokens de submodelos (ej: G3, G5, M5, M6 o G4)
            tokens = re.split(r"[\s,]+(?:o|y)?[\s,]*", tail)
            for t in tokens:
                t_clean = t.strip()
                if re.match(r"^[A-Za-z0-9]{2,6}$", t_clean) and t_clean.lower() not in known_non_models and t_clean.lower() not in {"con", "para", "de", "en", "por", "que", "los"}:
                    full_name = f"{prefix} {t_clean.upper()}"
                    if full_name not in target_models:
                        target_models.append(full_name)

        # 2. Patrones individuales de modelos
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
                # Si el código es muy corto (<= 2 caracteres, ej: G4), solo se admite ligado a la marca
                if len(norm_check) < 3:
                    if brand:
                        raw_model = f"{brand} {raw_model.upper()}"
                    else:
                        continue

                if not any(raw_model.lower() == tm.lower() or raw_model.lower() in tm.lower() for tm in target_models):
                    target_models.append(raw_model)

        if not target_models:
            return None, [], []

        primary_model = target_models[0]
        safe_variants = self.build_model_variants(target_models, brand)
        return primary_model, target_models, safe_variants

    def build_model_variants(self, target_models: List[str], target_brand: Optional[str] = None) -> List[str]:
        """Genera y enriquece variantes normalizadas para una lista de modelos y su marca."""
        all_variants: set = set()
        modifiers = {"pro", "plus", "max", "ultra", "air"}
        brand_norm = target_brand.lower().strip() if target_brand else None

        for tm in target_models:
            all_variants.update(self.generate_model_variants(tm))

            parts = tm.split()
            # Si empieza con 'mini' (ej: Mini S12 Pro -> S12 Pro)
            if len(parts) >= 2 and parts[0].lower() == "mini":
                without_mini = " ".join(parts[1:])
                all_variants.update(self.generate_model_variants(without_mini))
                if brand_norm:
                    all_variants.add(f"{brand_norm} {without_mini.lower()}")
                    all_variants.add(f"{brand_norm}-{without_mini.lower()}")

            # Si termina con modificador (ej: S12 Pro)
            if len(parts) >= 2 and parts[-1].lower() in modifiers:
                base_model = " ".join(parts[:-1])
                mod = parts[-1].lower()
                if base_model.lower().startswith("mini "):
                    core = base_model[5:]
                    all_variants.update(self.generate_model_variants(f"{core} {mod}"))
                    if brand_norm:
                        all_variants.add(f"{brand_norm} {core.lower()} {mod}")
                        all_variants.add(f"{brand_norm} {core.lower()}")

            if brand_norm:
                all_variants.add(f"{brand_norm} {tm.lower()}")
                all_variants.add(f"{brand_norm}-{tm.lower()}")

        # Eliminar posibles tokens genéricos aislados que causarían falsos positivos
        dangerous_tokens = {"mini", "pro", "plus", "max", "ultra", "air"}
        if brand_norm:
            dangerous_tokens.update({f"{brand_norm} mini", f"{brand_norm} pro", f"{brand_norm} plus"})
        safe_variants = {v for v in all_variants if v not in dangerous_tokens and len(v) >= 3}

        return sorted(list(safe_variants))

    def extract_target_model(self, text: str) -> Tuple[Optional[str], List[str]]:
        """
        Detecta identificadores o códigos de modelo específicos solicitados por el usuario
        (ej: EQi12, S12 Pro, NucBox G3, MP100 Pro, SER5, Cubi 5) y genera sus variantes normalizadas.
        """
        primary, _, variants = self.extract_target_models(text)
        return primary, variants

    def extract_hardware_limits(self, text: str) -> Tuple[Optional[int], Optional[int]]:
        """Extrae requisitos mínimos de RAM (GB) y almacenamiento SSD (GB)."""
        text_lower = text.lower()
        min_ram = None
        min_storage = None

        # Requisito de RAM
        m_ram = re.search(r"(?:como mínimo|mínimo|al menos|desde)\s*(\d{1,2})\s*gb\s*(?:de\s*)?ram", text_lower)
        if not m_ram:
            m_ram = re.search(r"(\d{1,2})\s*gb\s*(?:de\s*)?ram\s*(?:como mínimo|mínimo|o más)", text_lower)
        if not m_ram:
            m_ram = re.search(r"(?:con|de)?\s*(\d{1,2})\s*gb\s*(?:de\s*)?ram\b", text_lower)
        if m_ram:
            min_ram = int(m_ram.group(1))

        # Requisito de almacenamiento SSD
        m_storage = re.search(r"(?:como mínimo|mínimo|al menos|desde)\s*(\d{3,4})\s*gb(?:\s*o\s*(\d)\s*tb)?\s*(?:de\s*)?(?:ssd|disco|almacenamiento)", text_lower)
        if not m_storage:
            m_storage = re.search(r"(?:con|de)?\s*(\d{3,4})\s*gb\s*(?:de\s*)?(?:ssd|disco|almacenamiento|rom)\b", text_lower)
        if m_storage:
            min_storage = int(m_storage.group(1))
        else:
            m_tb = re.search(r"(?:como mínimo|mínimo|al menos|con|de)?\s*(\d)\s*tb\s*(?:de\s*)?(?:ssd|disco|almacenamiento)?\b", text_lower)
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
            "nacional", "espana", "union", "europea", "ue", "cueste", "cuesta",
            "modelo", "modelos", "version", "versiones", "serie", "series"
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
        target_model: Optional[str] = None,
        target_models: Optional[List[str]] = None,
        target_brand: Optional[str] = None,
    ) -> List[str]:
        """
        Construye consultas segmentadas de alta precisión para los buscadores de las tiendas.
        Preserva la marca objetivo y garantiza que la consulta original no se pierda.
        """
        base_product = "mini pc" if "mini pc" in clean_query.lower() else clean_query.split()[0]
        ram_str = f"{min_ram_gb}gb" if min_ram_gb else ""
        storage_str = f"{min_storage_gb}gb" if min_storage_gb else ""
        brand_clean = target_brand.lower().strip() if target_brand else ""

        queries = []

        models_to_query = target_models or ([target_model] if target_model else [])

        # Si hay múltiples modelos específicos (ej: Mini S12 Pro, EQ12, SEi12, EQi12),
        # priorizar consultas individuales por cada modelo para que las tiendas encuentren todos los modelos
        if len(models_to_query) > 1:
            for tm in models_to_query:
                model_clean = tm.lower()
                q_brand_model = f"{brand_clean} {model_clean}".strip() if brand_clean and brand_clean not in model_clean else model_clean
                if q_brand_model not in queries:
                    queries.append(q_brand_model)
                q_brand_model_pc = f"{q_brand_model} {base_product}".strip()
                if q_brand_model_pc not in queries:
                    queries.append(q_brand_model_pc)
        else:
            # 1. Consulta limpia completa como prioridad para búsquedas normales de un solo modelo o genéricas
            if clean_query and clean_query not in queries:
                queries.append(clean_query)

        # 2. Consultas combinadas con modelo y marca
        for tm in models_to_query[:5]:
            model_clean = tm.lower()
            if brand_clean and brand_clean not in model_clean:
                q_brand_model = f"{brand_clean} {model_clean}"
                if q_brand_model not in queries:
                    queries.append(q_brand_model)
                q_brand_model_pc = f"{brand_clean} {model_clean} {base_product}"
                if q_brand_model_pc not in queries:
                    queries.append(q_brand_model_pc)

            q_base = f"{base_product} {model_clean}"
            if q_base not in queries:
                queries.append(q_base)

            if ram_str:
                q_ram = f"{brand_clean} {model_clean} {ram_str}".strip() if brand_clean else f"{base_product} {model_clean} {ram_str}"
                if q_ram not in queries:
                    queries.append(q_ram)

            # Solo añadir la subquery de modelo suelto si no es un código corto genérico (<= 3 caracteres)
            if len(model_clean) > 3 and model_clean not in queries and not (len(model_clean.split()) == 1 and len(model_clean) <= 4):
                queries.append(model_clean)

        # 3. Consultas dirigidas por procesador
        if allowed_cpus:
            for cpu in allowed_cpus[:6]:
                q_parts = []
                if brand_clean:
                    q_parts.append(brand_clean)
                q_parts.extend([base_product, cpu.lower()])
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

    def _build_criteria_from_llm(self, prompt: str, data: Dict[str, Any]) -> SearchCriteria:
        """Construye un SearchCriteria a partir de la interpretación semántica universal del LLM."""
        category_raw = str(data.get("category", "")).lower()
        category = ProductCategory.GENERAL_TECH
        for pc in ProductCategory:
            if pc.value == category_raw or pc.name.lower() == category_raw:
                category = pc
                break

        product_type_label = data.get("product_type") or "Dispositivo tecnológico"
        product_type = re.sub(r"[^a-z0-9_]", "_", self.strip_accents(product_type_label).lower())
        raw_brand = data.get("brand")
        target_brand = str(raw_brand).strip().title() if raw_brand and str(raw_brand).lower() != "null" else None
        raw_model = data.get("model")
        target_model = str(raw_model).strip() if raw_model and str(raw_model).lower() != "null" else None
        target_models = [target_model] if target_model else []
        target_model_variants = self.generate_model_variants(target_model) if target_model else []

        # Enriquecer con detección precisa de modelos múltiples si están presentes en el prompt
        rule_primary, rule_models, rule_variants = self.extract_target_models(prompt)
        if rule_models:
            # Si el modelo devuelto por el LLM era una lista en texto ("G3, G5, M5"), reemplazar con lista limpia
            if any("," in tm for tm in target_models) or not target_models:
                target_models = rule_models
                target_model = rule_primary
            else:
                for rm in rule_models:
                    if rm not in target_models:
                        target_models.append(rm)
            target_model_variants = sorted(list(set(target_model_variants + rule_variants)))

        clean_query = data.get("clean_query") or self.clean_search_query(prompt, category)

        # Precios
        min_price = data.get("min_price")
        max_price = data.get("max_price")
        if min_price is None or max_price is None:
            regex_min, regex_max = self.extract_budget(prompt)
            if min_price is None:
                min_price = regex_min
            if max_price is None:
                max_price = regex_max

        # Hardware y CPUs
        allowed_cpus = self.extract_allowed_cpus(prompt)
        min_ram_gb, min_storage_gb = self.extract_hardware_limits(prompt)

        key_specs = [str(s).strip() for s in data.get("key_specs", []) if s and str(s).strip()]
        for ks in self.extract_key_specs(prompt):
            if ks not in key_specs:
                key_specs.append(ks)

        is_generic = bool(data.get("is_generic", False))

        refinement_aspects: List[RefinementAspect] = []
        for aspect in data.get("refinement_aspects", []):
            if isinstance(aspect, dict) and aspect.get("question") and aspect.get("options"):
                refinement_aspects.append(
                    RefinementAspect(
                        key=aspect.get("key", "aspect"),
                        question=aspect.get("question"),
                        options=aspect.get("options", []),
                        recommended_option=aspect.get("recommended_option"),
                    )
                )

        # Si es un equipo informático y faltan especificaciones de hardware, garantizar que se pregunte
        if product_type in ["mini_pc", "laptop", "desktop"] and not min_ram_gb and not min_storage_gb:
            is_generic = True
            # Asegurar que se pregunte por CPU si el LLM no lo incluyó
            if not any("cpu" in a.key.lower() or "procesador" in a.key.lower() for a in refinement_aspects):
                insert_idx = 1 if refinement_aspects and refinement_aspects[0].key == "barebone" else 0
                refinement_aspects.insert(
                    insert_idx,
                    RefinementAspect(
                        key="cpu",
                        question="Preferencia de procesador / arquitectura",
                        options=[
                            "AMD Ryzen (Ryzen 5 / Ryzen 7)",
                            "Intel (Alder Lake N100 / Core i3 / Core i5)",
                            "Gama Alta (Ryzen 7 / Core i7 o superior)",
                            "Cualquiera / Sin preferencia",
                        ],
                        recommended_option="Cualquiera / Sin preferencia",
                    )
                )

        if refinement_aspects and (not min_ram_gb or not min_storage_gb):
            is_generic = True

        target_queries = self.build_targeted_queries(
            clean_query,
            allowed_cpus,
            min_ram_gb,
            min_storage_gb,
            target_model=target_model,
            target_models=target_models,
            target_brand=target_brand,
        )

        _, backend_label = LLMClient.get_backend_info()

        return SearchCriteria(
            raw_query=prompt,
            clean_query=clean_query,
            category=category,
            product_type=product_type,
            product_type_label=product_type_label,
            target_brand=target_brand,
            target_series=target_model,
            min_system_price=35.0,
            min_price=min_price,
            max_price=max_price,
            key_specs=key_specs,
            must_have_keywords=[],
            exclude_keywords=self.extract_exclusions(prompt),
            min_ram_gb=min_ram_gb,
            min_storage_gb=min_storage_gb,
            allowed_cpus=allowed_cpus,
            max_price_by_cpu=self.extract_conditional_prices(prompt),
            target_search_queries=target_queries,
            target_model=target_model,
            target_models=target_models,
            target_model_variants=target_model_variants,
            min_score_threshold=80.0,
            ships_from_spain_only=True,
            in_stock_only=True,
            is_generic=is_generic,
            refinement_aspects=refinement_aspects,
            analysis_engine=backend_label,
        )

    def _build_criteria_from_rules(self, prompt: str) -> SearchCriteria:
        """Construye un SearchCriteria mediante reglas heurísticas locales (modo sin IA / offline)."""
        exclusion_markers = r"\b(?:descartando|excluyendo|evitando|sin\s+(?:procesador|equipos?|marcas?|amd|celeron)|no\s+quiero|nada\s+de|quitar|obviar)\b"
        parts = re.split(exclusion_markers, prompt, flags=re.I)
        positive_text = parts[0]
        negative_text = " ".join(parts[1:]) if len(parts) > 1 else ""

        category = self.detect_category(positive_text)
        product_type, product_type_label = self.detect_product_type(positive_text, category)
        target_brand = self.detect_brand(positive_text)

        min_price, max_price = self.extract_budget(prompt)
        max_price_by_cpu = self.extract_conditional_prices(prompt)
        if max_price_by_cpu and (max_price is None or max(max_price_by_cpu.values()) > max_price):
            max_price = max(max_price_by_cpu.values())

        target_model, target_models, target_model_variants = self.extract_target_models(positive_text)
        target_series = target_models[0] if target_models else None

        allowed_cpus = self.extract_allowed_cpus(positive_text)
        min_ram_gb, min_storage_gb = self.extract_hardware_limits(positive_text)
        key_specs = self.extract_key_specs(positive_text)
        exclude_keywords = self.extract_exclusions(negative_text)
        clean_query = self.clean_search_query(prompt, category)

        target_queries = self.build_targeted_queries(
            clean_query,
            allowed_cpus,
            min_ram_gb,
            min_storage_gb,
            target_model=target_model,
            target_models=target_models,
            target_brand=target_brand,
        )

        # Si es un equipo informático y no se especificó RAM o disco, marcar como genérico
        is_generic = False
        refinement_aspects: List[RefinementAspect] = []
        if product_type in ["mini_pc", "laptop", "desktop"] and not min_ram_gb and not min_storage_gb:
            is_generic = True
            refinement_aspects = [
                RefinementAspect(
                    key="barebone",
                    question="¿Aceptas equipos Barebone (sin RAM ni disco para montarlos tú) o solo completos con Windows?",
                    options=[
                        "Solo equipos completos listos para usar",
                        "Solo Barebones (sin RAM ni disco)",
                        "Cualquiera / Me da igual",
                    ],
                    recommended_option="Solo equipos completos listos para usar",
                ),
                RefinementAspect(
                    key="cpu",
                    question="Preferencia de procesador / arquitectura",
                    options=[
                        "AMD Ryzen (Ryzen 5 / Ryzen 7)",
                        "Intel (Alder Lake N100 / Core i3 / Core i5)",
                        "Gama Alta (Ryzen 7 / Core i7 o superior)",
                        "Cualquiera / Sin preferencia",
                    ],
                    recommended_option="Cualquiera / Sin preferencia",
                ),
                RefinementAspect(
                    key="ram",
                    question="Memoria RAM mínima deseada",
                    options=["16 GB (Recomendado)", "32 GB", "8 GB", "Cualquiera / Sin mínimo"],
                    recommended_option="16 GB (Recomendado)",
                ),
                RefinementAspect(
                    key="storage",
                    question="Almacenamiento SSD mínimo deseado",
                    options=["512 GB SSD (Recomendado)", "1 TB SSD", "256 GB SSD", "Cualquiera / Sin mínimo"],
                    recommended_option="512 GB SSD (Recomendado)",
                ),
            ]

        return SearchCriteria(
            raw_query=prompt,
            clean_query=clean_query,
            category=category,
            product_type=product_type,
            product_type_label=product_type_label,
            target_brand=target_brand,
            target_series=target_series,
            min_system_price=35.0,
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
            target_models=target_models,
            target_model_variants=target_model_variants,
            min_score_threshold=80.0,
            ships_from_spain_only=True,
            in_stock_only=True,
            is_generic=is_generic,
            refinement_aspects=refinement_aspects,
            analysis_engine="Reglas Locales Heurísticas (Modo sin IA)",
        )

    def analyze_user_prompt(self, prompt: str) -> SearchCriteria:
        """
        Analiza integralmente la entrada del usuario y genera un SearchCriteria estructurado.
        Si hay un motor LLM activo (Ollama local, Gemini, OpenAI), utiliza razonamiento semántico universal.
        En caso contrario o si falla la conexión, recurre automáticamente al motor de reglas locales.
        """
        try:
            llm_data = LLMClient.analyze_query(prompt)
            if llm_data and isinstance(llm_data, dict):
                return self._build_criteria_from_llm(prompt, llm_data)
        except Exception:
            pass

        return self._build_criteria_from_rules(prompt)

    def refine_criteria(self, criteria: SearchCriteria, selected_options: Dict[str, str]) -> SearchCriteria:
        """
        Aplica las opciones seleccionadas por el usuario en el paso interactivo de afinado
        y actualiza las restricciones y consultas dirigidas hacia las tiendas.
        """
        for key, chosen_text in selected_options.items():
            if not chosen_text:
                continue
            text_lower = chosen_text.lower()
            if text_lower.startswith("cualquiera") or "indiferente" in text_lower or "me da igual" in text_lower or "sin minimo" in text_lower:
                continue

            k_lower = key.lower()

            # 1. Parámetro RAM
            if "ram" in k_lower or "memoria" in k_lower:
                m = re.search(r"(\d+)\s*GB", chosen_text, re.I)
                if m:
                    criteria.min_ram_gb = int(m.group(1))

            # 2. Parámetro Almacenamiento SSD
            elif any(s in k_lower for s in ["storage", "almacenamiento", "ssd", "disco"]):
                m = re.search(r"(\d+)\s*(GB|TB)", chosen_text, re.I)
                if m:
                    val = int(m.group(1))
                    if m.group(2).upper() == "TB":
                        val *= 1024
                    criteria.min_storage_gb = val

            # 3. Parámetro Procesador / CPU
            elif any(s in k_lower for s in ["cpu", "procesador", "architecture", "arquitectura"]):
                if "amd" in text_lower or "ryzen" in text_lower:
                    criteria.allowed_cpus = ["Ryzen"]
                    if "Ryzen" not in criteria.key_specs:
                        criteria.key_specs.append("Ryzen")
                elif "intel" in text_lower:
                    criteria.allowed_cpus = ["Intel", "Core", "N100", "N95", "i3", "i5", "i7"]
                    if "Intel" not in criteria.key_specs:
                        criteria.key_specs.append("Intel")
                elif "gama alta" in text_lower:
                    criteria.allowed_cpus = ["Ryzen 7", "Ryzen 9", "i7", "i9", "Core Ultra"]
                    if "Gama Alta" not in criteria.key_specs:
                        criteria.key_specs.append("Gama Alta")
                else:
                    clean_choice = re.sub(r"\(.*?\)", "", chosen_text).strip()
                    if clean_choice:
                        criteria.allowed_cpus = [clean_choice]
                        if clean_choice not in criteria.key_specs:
                            criteria.key_specs.append(clean_choice)

            # 4. Parámetro Barebone
            elif "barebone" in k_lower:
                if "completos" in text_lower or text_lower.startswith("no") or "sin barebone" in text_lower:
                    if "barebone" not in criteria.exclude_keywords:
                        criteria.exclude_keywords.append("barebone")
                elif "solo barebone" in text_lower or text_lower.startswith("s") or "si" in text_lower:
                    if "barebone" not in criteria.must_have_keywords:
                        criteria.must_have_keywords.append("barebone")

            # 5. Parámetros universales de cualquier producto (ej: café, presión, potencia, motor)
            else:
                clean_choice = re.sub(r"\(.*?\)", "", chosen_text).strip()
                if clean_choice and clean_choice not in criteria.key_specs:
                    criteria.key_specs.append(clean_choice)
                    refined_q = f"{criteria.clean_query} {clean_choice}"
                    if refined_q not in criteria.target_search_queries:
                        criteria.target_search_queries.insert(1, refined_q)

        # Regenerar consultas dirigidas si se especificó CPU, RAM o disco
        if criteria.min_ram_gb or criteria.min_storage_gb or criteria.allowed_cpus:
            criteria.target_search_queries = self.build_targeted_queries(
                criteria.clean_query,
                criteria.allowed_cpus,
                criteria.min_ram_gb,
                criteria.min_storage_gb,
                target_model=criteria.target_model,
                target_models=criteria.target_models,
                target_brand=criteria.target_brand,
            )

        return criteria

    def get_suggested_specs(self, category: ProductCategory) -> List[str]:
        """Devuelve consejos y especificaciones clave a tener en cuenta según categoría."""
        return self.SUGGESTED_SPECS_BY_CATEGORY.get(category, [
            "Verificar garantía oficial de 3 años en España",
            "Comprobar disponibilidad y costes de envío"
        ])

