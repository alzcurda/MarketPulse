import re
import unicodedata
from typing import Dict, List, Optional, Tuple
from marketpulse.models import DiscardReason, DiscardRecord, ProductCategory, ProductResult, SearchCriteria


class Aggregator:
    """
    Agregador y motor de ranking con sistema de auditoría y diagnóstico de descartes.
    Recibe los resultados de las tiendas consultadas, filtra por restricciones,
    calcula la puntuación de afinidad y ordena los productos para la comparativa.
    """

    def __init__(self):
        self.last_discard_records: List[DiscardRecord] = []

    def _record_discard(self, product: ProductResult, reason: DiscardReason, detail: str):
        """Registra un producto descartado y la causa técnica exacta del descarte."""
        self.last_discard_records.append(
            DiscardRecord(product=product, reason=reason, detail=detail)
        )

    def get_discard_summary(self) -> Dict[str, int]:
        """Devuelve un resumen del conteo de descartes agrupado por motivo."""
        summary: Dict[str, int] = {}
        for rec in self.last_discard_records:
            label = rec.reason.value
            summary[label] = summary.get(label, 0) + 1
        return summary

    # Categorías ajenas que deben ser descartadas cuando se buscan equipos informáticos
    NON_COMPUTING_PATTERNS = [
        r"\bcampana\s+extractora\b",
        r"\bextractor\b",
        r"\bfrigor[ií]fico\b",
        r"\blavadora\b",
        r"\blavavajillas\b",
        r"\bsecadora\b",
        r"\bhorno\b",
        r"\bmicroondas\b",
        r"\bcafetera\b",
        r"\bfreidora\b",
        r"\baspirador[a]?\b",
        r"\baspi\b",
        r"\brobot\s+aspirador\b",
        r"\bbatidora\b",
        r"\btostador[a]?\b",
        r"\bplancha\b",
        r"\bcalefactor\b",
        r"\baire\s+acondicionado\b",
        r"\bhumidificador\b",
        r"\bdeshumidificador\b",
        r"\bcuchill[oa]s?\b",
        r"\bnavajas?\b",
        r"\bbater[ií]as?\b",
        r"\bintercomunicador(?:es)?\b",
        r"\bcascos?\s+(?:de\s+moto|para\s+casco|moto|ciclismo)\b",
        r"\bjuguetes?\b",
        r"\bvideojuego\b",
        r"\bjuego\s+(?:ps4|ps5|xbox|switch|nintendo)\b",
        r"\bfigura\b",
        r"\bfunko\b",
        r"\blibro\b",
        r"\bnovela\b",
        r"\bpatinete\b",
        r"\bsmartwatch\b",
        r"\bpulsera\s+de\s+actividad\b",
        r"\bfunda\s+para\s+m[oó]vil\b",
        r"\bcristal\s+templado\b",
        r"\bbombill[ao]s?\b",
        r"\bhal[oó]gen[ao]s?\b",
        r"\bl[aá]mparas?\b",
        r"\bcasquillos?\b",
        r"\bfocos?\b",
        r"\bdownlights?\b",
        r"\btiras?\s+led\b",
        r"\bplaf[oó]n(?:es)?\b",
        r"\bluz\s+(?:c[aá]lida|fr[ií]a|blanca|neutra)\b",
        r"\bbulbs?\b",
        r"\bled\s*12v\b",
        r"\b12v\s*led\b",
        r"\b12v\s*20w\b",
        r"\b12v\s*10w\b",
        r"\b2-pin\b",
        r"\bbi-pin\b",
        r"\bg4\s*(?:led|capsule|12v|20w|10w|hal[oó]gen|regulable|pin)\b",
        # Artículos deportivos ajenos a informática
        r"\braquetas?\s+de\s+(?:b[aá]dminton|tenis|p[aá]del|squash)\b",
        r"\bb[aá]dminton\b",
        r"\btenis\b",
        r"\bp[aá]del\b",
        r"\bsquash\b",
        r"\bcordaje\b",
        r"\bgrip\s+g\d\b",
        r"\bpala\s+de\s+p[aá]del\b",
        r"\bpelota[s]?\b",
        r"\bbal[oó]n(?:es)?\b",
    ]

    # Accesorios y componentes de repuesto que saturan las búsquedas de ordenadores/mini PCs
    ACCESSORY_PATTERNS = [
        r"\bdock(?:ing)?(?:\s+station)?\b",
        r"\bestaci[oó]n\s+de\s+acoplamiento\b",
        r"\bcarcasa(?:\s+vac[ií]a)?\b",
        r"\bcaja\s+vac[ií]a\b",
        r"\bsolo\s+caja\b",
        # Refrigeración / Ventiladores / Disipadores como repuesto
        r"^(?:ventilador|cooler|cooling\s+fan|cpu\s+fan|disipador|heatsink)\b",
        r"\b(?:ventilador|cooler|fan|disipador|heatsink)\s+(?:de\s+repuesto|de\s+refrigeraci[oó]n)?\s*(?:para|for|pour|compatibl[ey]\s+con)\b",
        r"\bventilador\s+de\s+refrigeraci[oó]n\b",
        r"\bcpu\s+cooling\s+fan\b",
        r"\bpasta\s+t[eé]rmica\b",
        r"\bpad\s+t[eé]rmico\b",
        # Soportes, brackets y raquetas de montaje
        r"\braqueta(?:s)?\b",
        r"\bbracket[s]?\b",
        r"\bsoporte(?:s)?(?:\s+vesa|\s+para|\s+de\s+pared|\s+de\s+mesa|\s+met[aá]lico)?\b",
        r"\badaptador\s+vesa\b",
        r"\bplaca(?:s)?\s+de\s+montaje\b",
        r"\bchapa(?:s)?\s+de\s+montaje\b",
        r"\banclaje(?:s)?\b",
        r"\brail(?:es)?\s+de\s+montaje\b",
        r"\bbrazo\s+(?:articulado|para\s+monitor)\b",
        # Fuentes y adaptadores de corriente
        r"\bfuente\s+de\s+alimentaci[oó]n\b",
        r"\bpower\s+supply\b",
        r"\badaptador\s+de\s+corriente\b",
        r"\bpower\s+adapter\b",
        r"\btransformador\b",
        r"\balimentador\b",
        r"\bcargador\b",
        # Cables y tornillería
        r"\bcable\b",
        r"\bconector\s+(?:sata|flex|dc|jack)\b",
        r"\btornillo[s]?\b",
        r"\bkit\s+de\s+tornillos\b",
        r"\bantena(?:s)?(?:\s+wifi)?\b",
        # Repuestos y recambios
        r"\brepuesto[s]?\b",
        r"\brecambio[s]?\b",
        r"\breemplazo[s]?\b",
        r"\bpieza(?:s)?\s+de\s+repuesto\b",
        r"\bspare\s+parts?\b",
        # Fundas y transporte
        r"\bfunda\b",
        r"\bestuche(?:s)?\b",
        r"\bbolsa\s+de\s+transporte\b",
        r"\bmalet[ií]n\b",
        r"\bpegatina\b",
        r"\bvinilo\b",
        r"\bprotector\b",
        # Patrones relacionales de accesorios dedicados a un modelo de equipo
        r"\b(?:para|for|pour|f[uü]r|compatibl[ey]\s+con|dedicado\s+a)\s+(?:mini\s*pc|elitedesk|prodesk|thinkcentre|nuc|nucbox|trigkey|beelink|gmktec|minisforum|chuwi|ordenador)\b",
    ]

    # Procesadores de gama alta que exigen control de sensatez de precio (> 400€)
    HIGH_END_CPU_PATTERN = r"\b(CORE\s+ULTRA|I9-(?:1[0-4]\d{3}|[7-9]\d{3})[A-Z0-9]*|CORE\s+I9|RYZEN\s+(?:AI\s+MAX|9\b|9\s*\d{4})|THREADRIPPER|XEON)\b"

    @staticmethod
    def _strip_accents(text: str) -> str:
        """Elimina acentos y normaliza a minúsculas para comparaciones semánticas fiables."""
        return "".join(
            c for c in unicodedata.normalize("NFD", text)
            if unicodedata.category(c) != "Mn"
        ).lower()

    def calculate_match_score(self, product: ProductResult, criteria: SearchCriteria) -> float:
        """
        Calcula una puntuación de afinidad (0 a 100) en base a la coincidencia con
        las especificaciones deseadas, el modelo objetivo y el término de búsqueda.
        """
        score = 25.0
        title_norm = self._strip_accents(product.title)
        title_nospace = title_norm.replace(" ", "")
        title_upper = product.title.upper()
        matched_specs = []

        # 1. Coincidencia con modelo específico si fue solicitado
        target_models = criteria.target_models or ([criteria.target_model] if criteria.target_model else [])
        if target_models:
            variants = criteria.target_model_variants or target_models
            model_matched = False
            matched_model_name = None
            for v in variants:
                v_norm = self._strip_accents(v)
                if re.search(rf"(?<![a-z0-9]){re.escape(v_norm)}(?![a-z0-9])", f" {title_norm} "):
                    model_matched = True
                    matched_model_name = v
                    break
            if model_matched:
                score += 35.0
                matched_specs.append(matched_model_name or target_models[0])
        else:
            # Coincidencia con palabras clave de la consulta limpia
            clean_q = self._strip_accents(criteria.clean_query)
            query_words = [w for w in clean_q.split() if len(w) >= 2]
            if query_words:
                matched_words = sum(1 for w in query_words if w in title_norm or w in title_nospace)
                ratio = matched_words / len(query_words)
                points_possible = 50.0 if not criteria.allowed_cpus else 25.0
                score += ratio * points_possible

        # 2. Coincidencia de procesadores permitidos
        if criteria.allowed_cpus:
            matched_cpu = False
            for cpu in criteria.allowed_cpus:
                if re.search(rf"\b{re.escape(cpu.upper())}\b", title_upper):
                    matched_cpu = True
                    matched_specs.append(cpu)
                    break
            if matched_cpu:
                score += 25.0

        # 3. Coincidencia de RAM y almacenamiento exigidos
        if criteria.min_ram_gb and re.search(rf"\b{criteria.min_ram_gb}\s*G", title_upper):
            score += 10.0
            matched_specs.append(f"{criteria.min_ram_gb}GB RAM")
        if criteria.min_storage_gb and (
            re.search(rf"\b{criteria.min_storage_gb}\s*G", title_upper) or
            ("TB" in title_upper and criteria.min_storage_gb >= 512)
        ):
            score += 10.0
            matched_specs.append(f"{criteria.min_storage_gb}GB SSD")

        # 4. Coincidencia con especificaciones técnicas clave adicionales
        for spec in criteria.key_specs:
            spec_norm = self._strip_accents(spec)
            spec_nospace = spec_norm.replace(" ", "")
            if spec_norm in title_norm or spec_nospace in title_nospace:
                if spec not in matched_specs:
                    score += 10.0
                    matched_specs.append(spec)

        product.matched_specs = matched_specs

        # 5. Comprobación de presupuesto
        if criteria.max_price or criteria.max_price_by_cpu:
            exceeded = False
            if criteria.max_price and product.price > criteria.max_price:
                exceeded = True
            if criteria.max_price_by_cpu:
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.upper() in title_upper and product.price > p_max:
                        exceeded = True
                        break
            if exceeded:
                score -= 40.0
            elif product.price > 0:
                score += 10.0
        elif product.price > 0:
            score += 10.0

        # 6. Bonus por disponibilidad y envío desde España
        if product.in_stock:
            score += 5.0
        if product.ships_from_spain:
            score += 5.0

        # 7. Bonus por descuento activo
        if product.discount_percentage and product.discount_percentage > 5:
            score += min(product.discount_percentage * 0.2, 5.0)

        return max(0.0, min(100.0, round(score, 1)))

    def classify_candidate_item(self, title: str, price: float = 0.0) -> Tuple[str, str]:
        """
        Categoriza semánticamente el artículo candidato a partir de su título y precio.
        Devuelve (item_type_id, label_legible) para contrastar que la tipología del producto
        sea la misma o similar a lo solicitado (un Mini PC no tiene nada que ver con un ventilador o raqueta).
        """
        title_norm = self._strip_accents(title)

        # 1. Material deportivo (raqueta, bádminton, tenis, pádel, pelotas)
        if re.search(r"\b(raquetas?\s+de\s+(?:b[aá]dminton|tenis|p[aá]del|squash)|b[aá]dminton|tenis|p[aá]del|squash|cordaje|grip\s+g\d|pala\s+de\s+p[aá]del|pelota[s]?|bal[oó]n(?:es)?)\b", title_norm):
            return "sports_equipment", "Material deportivo (Raqueta / Bádminton / Tenis)"

        # 2. Iluminación (bombillas, halógenas, casquillos, focos)
        if re.search(r"\b(bombill[ao]s?|hal[oó]gen[ao]s?|l[aá]mparas?|casquillos?|focos?|downlights?|tiras?\s+led|plaf[oó]n(?:es)?|bulbs?|g4\s*(?:led|capsule|12v|20w|10w|hal[oó]gen|regulable|pin))\b", title_norm):
            return "lighting", "Iluminación (Bombilla / Lámpara)"

        # 3. Componentes de refrigeración (ventiladores sueltos, disipadores, coolers, pasta térmica)
        is_cooling = (
            re.match(r"^(?:ventilador|cooler|cooling\s+fan|cpu\s+fan|disipador|heatsink)\b", title_norm)
            or re.search(r"\b(?:ventilador|cooler|fan|disipador|heatsink)\s+(?:de\s+repuesto|de\s+refrigeraci[oó]n)?\s*(?:para|for|pour|compatibl[ey]\s+con)\b", title_norm)
            or re.search(r"\b(ventilador\s+de\s+refrigeraci[oó]n|cpu\s+cooling\s+fan|pasta\s+t[eé]rmica|pad\s+t[eé]rmico)\b", title_norm)
        )
        if is_cooling:
            return "cooling_component", "Componente de refrigeración (Ventilador / Disipador)"

        # 4. Soportes, brackets o raquetas de montaje
        is_mount = (
            re.match(r"^(?:soporte|bracket|raqueta\s+de\s+montaje|anclaje|chapa|placa\s+de\s+montaje)\b", title_norm)
            or re.search(r"\b(raqueta(?:s)?\b|bracket[s]?|soporte(?:s)?|placa(?:s)?\s+de\s+montaje|chapa(?:s)?\s+de\s+montaje|anclaje(?:s)?|brazo\s+(?:articulado|para\s+monitor))\s*(?:para|for|pour|compatibl[ey]\s+con|vesa|de\s+montaje)\b", title_norm)
        )
        if is_mount:
            return "mounting_bracket", "Soporte de montaje (Bracket / Raqueta VESA)"

        # 5. Fuentes de alimentación, cargadores y transformadores
        is_power = (
            re.match(r"^(?:fuente\s+de\s+alimentaci[oó]n|power\s+supply|adaptador\s+de\s+corriente|cargador|transformador)\b", title_norm)
            or re.search(r"\b(fuente\s+de\s+alimentaci[oó]n|power\s+supply|adaptador\s+de\s+corriente|power\s+adapter|transformador|cargador)\s*(?:para|for|pour|compatibl[ey]\s+con)\b", title_norm)
        )
        if is_power:
            return "power_supply", "Fuente de alimentación / Cargador"

        # 6. Cables, repuestos y módulos sueltos
        is_spare = (
            re.match(r"^(?:cable|conector|tornillo|kit\s+de\s+tornillos|repuesto|recambio|reemplazo|antena)\b", title_norm)
            or re.search(r"\b(m[oó]dulo\s+ram|memoria\s+ram|disco\s+ssd|cable\s+sata|cable\s+flex|repuesto[s]?|recambio[s]?|reemplazo[s]?)\s+(?:para|for|pour|compatibl[ey]\s+con)\b", title_norm)
        )
        if is_spare:
            return "spare_part", "Pieza de repuesto / Cable / Módulo suelto"

        # 7. Fundas, maletines, docks y carcasas vacías
        is_acc_case = re.search(r"\b(dock(?:ing)?\s+station|estaci[oó]n\s+de\s+acoplamiento|carcasa(?:\s+vac[ií]a)?|caja\s+vac[ií]a|funda|estuche|bolsa\s+de\s+transporte|malet[ií]n)\b", title_norm)
        if is_acc_case:
            return "accessory_case", "Accesorio (Funda / Dock / Carcasa)"

        # 8. Equipos informáticos completos
        if re.search(r"\b(mini\s*pc|minipc|micro\s*pc|microordenador|nucbox|mini\s*s(?:12)?|eqi-?\d+|eq-?\d+|ser[5-8]|sei[5-8]|cubi|prodesk\s+\d+|elitedesk\s+\d+|thinkcentre)\b", title_norm):
            return "mini_pc", "Mini PC (Equipo completo)"

        if re.search(r"\b(port[aá]til|laptop|notebook|macbook|ultrabook)\b", title_norm):
            return "laptop", "Portátil / Laptop"

        if re.search(r"\b(sobremesa|torre\s*pc|pc\s*gaming|ordenador\s*gaming)\b", title_norm):
            return "desktop", "Ordenador de Sobremesa / Torre"

        # Si incluye CPU + RAM/SSD de un ordenador y marca reconocida
        has_pc_hardware = (
            re.search(r"\b(n100|n95|n150|n200|n305|n300|ryzen|core\s*i[3579]|i[3579]-?\d{4,5})\b", title_norm)
            and re.search(r"\b(\d{1,2}\s*gb|\d{3}\s*gb|\d\s*tb)\b", title_norm)
        )
        if has_pc_hardware:
            return "mini_pc", "Mini PC (Equipo completo)"

        return "other", "Artículo general"

    def verify_product_type_integrity(
        self,
        product: ProductResult,
        criteria: SearchCriteria
    ) -> Tuple[bool, Optional[DiscardReason], Optional[str]]:
        """
        Verificador estricto de autenticidad del tipo de artículo:
        Categoriza el artículo devuelto por la tienda y comprueba que corresponda auténticamente
        a la tipología solicitada por el usuario (un Mini PC no tiene nada que ver con un ventilador o una raqueta).
        """
        cand_type, cand_label = self.classify_candidate_item(product.title, product.price)
        title_norm = self._strip_accents(product.title)

        is_computer_target = criteria.product_type in ["mini_pc", "laptop", "desktop"] or (
            criteria.category in [ProductCategory.PC_COMPONENTS, ProductCategory.LAPTOPS]
            and any(w in criteria.clean_query.lower() for w in ["mini pc", "portatil", "laptop", "sobremesa", "ordenador"])
        )

        if is_computer_target:
            target_label = criteria.product_type_label or "Ordenador completo"

            # 1. Material deportivo (raqueta de bádminton, tenis, etc.)
            if cand_type == "sports_equipment":
                return False, DiscardReason.CATEGORY_MISMATCH, f"Artículo categorizado como '{cand_label}', ajeno a un {target_label}"

            # 2. Iluminación (bombillas, casquillos G4, etc.)
            if cand_type == "lighting":
                return False, DiscardReason.CATEGORY_MISMATCH, f"Artículo categorizado como '{cand_label}', ajeno a un {target_label}"

            # 3. Componentes de refrigeración (ventilador, cooler, disipador)
            if cand_type == "cooling_component":
                return False, DiscardReason.COMPONENT_OR_SPARE_PART, f"Artículo categorizado como '{cand_label}' en lugar del equipo completo ({target_label})"

            # 4. Soportes o brackets (raqueta de montaje, soporte VESA)
            if cand_type == "mounting_bracket":
                return False, DiscardReason.COMPONENT_OR_SPARE_PART, f"Artículo categorizado como '{cand_label}' en lugar del equipo completo ({target_label})"

            # 5. Fuentes de alimentación o cargadores
            if cand_type == "power_supply":
                return False, DiscardReason.COMPONENT_OR_SPARE_PART, f"Artículo categorizado como '{cand_label}' en lugar del equipo completo ({target_label})"

            # 6. Piezas de repuesto o módulos sueltos
            if cand_type == "spare_part":
                return False, DiscardReason.COMPONENT_OR_SPARE_PART, f"Artículo categorizado como '{cand_label}' en lugar del equipo completo ({target_label})"

            # 7. Accesorios (fundas, docks, carcasas)
            if cand_type == "accessory_case":
                return False, DiscardReason.ACCESSORY, f"Artículo categorizado como '{cand_label}' en lugar del equipo completo ({target_label})"

            # 8. Mismatch de formato de ordenador (ej: portátil cuando se busca mini PC)
            if criteria.product_type == "mini_pc" and cand_type in ["laptop", "desktop"]:
                return False, DiscardReason.PRODUCT_TYPE_MISMATCH, f"Artículo categorizado como '{cand_label}' en lugar de {target_label}"

            # 9. Para mini PC, descartar artículos no identificados que carezcan de indicadores de ordenador/hardware
            if criteria.product_type == "mini_pc" and cand_type == "other":
                has_pc_indicator = bool(re.search(
                    r"\b(mini\s*pc|minipc|micro\s*pc|barebone|nucbox|ordenador|computadora|sobremesa|pc|desktop|ryzen|core|intel|amd|windows|linux|ddr[45]|nvme|ssd)\b",
                    title_norm
                ))
                if not has_pc_indicator:
                    return False, DiscardReason.PRODUCT_TYPE_MISMATCH, f"Artículo no identificado como {target_label}"

        return True, None, None

    def filter_and_rank(self, raw_results: List[ProductResult], criteria: SearchCriteria) -> List[ProductResult]:
        """
        Aplica filtros y ordena los resultados de múltiples tiendas según reglas estrictas:
        - Coincidencia obligatoria de token de modelo
        - Aislamiento estricto de categoría (no electrodomésticos ni no-IT)
        - Control de sensatez precio vs hardware (Core Ultra/i9/Ryzen 9 >= 400€, no docks)
        - Umbral de afinidad mínima (score >= 80%)
        Registra cada descarte en self.last_discard_records para auditoría y diagnóstico transparente.
        """
        filtered: List[ProductResult] = []
        seen_urls = set()
        self.last_discard_records = []

        for prod in raw_results:
            # 1. Deduplicación por URL
            if prod.url in seen_urls:
                self._record_discard(prod, DiscardReason.DUPLICATE_URL, "Enlace duplicado ya indexado previamente")
                continue
            seen_urls.add(prod.url)

            # 2. Descartar enlaces a páginas de búsqueda o títulos ficticios
            url_lower = prod.url.lower()
            if any(p in url_lower for p in ["/s?k=", "/w/wholesale-", "/buscar/?query=", "/search.html?query="]):
                self._record_discard(prod, DiscardReason.SEARCH_PAGE_OR_PLACEHOLDER, "URL de búsqueda en tienda en lugar de producto")
                continue
            if prod.title.startswith("Resultados ") or prod.title.startswith("[Acceso directo"):
                self._record_discard(prod, DiscardReason.SEARCH_PAGE_OR_PLACEHOLDER, "Marcador de posición de búsqueda ficticio")
                continue

            title_lower = prod.title.lower()
            title_upper = prod.title.upper()

            # 3. Aislamiento de categoría (eliminar electrodomésticos, videojuegos, etc. en IT)
            is_computing_category = criteria.category in [
                ProductCategory.PC_COMPONENTS,
                ProductCategory.LAPTOPS,
                ProductCategory.GENERAL_TECH,
            ]
            if is_computing_category:
                matched_non_comp = next((pat for pat in self.NON_COMPUTING_PATTERNS if re.search(pat, title_lower)), None)
                if matched_non_comp:
                    clean_pat = re.sub(r"[\\b^$]", "", matched_non_comp)
                    self._record_discard(prod, DiscardReason.CATEGORY_MISMATCH, f"Artículo ajeno a informática ({clean_pat})")
                    continue

            # 4. Filtrar accesorios (docks, carcasas, soportes vesa, fundas, cables)
            query_has_accessory = any(re.search(pat, criteria.clean_query.lower()) for pat in self.ACCESSORY_PATTERNS)
            if not query_has_accessory:
                matched_acc = next((pat for pat in self.ACCESSORY_PATTERNS if re.search(pat, title_lower)), None)
                if matched_acc:
                    clean_pat = re.sub(r"[\\b^$]", "", matched_acc)
                    self._record_discard(prod, DiscardReason.ACCESSORY, f"Accesorio o periférico ({clean_pat})")
                    continue

            # 4b. Verificador adicional de autenticidad del tipo de artículo (equipos completos vs ventiladores/raquetas/repuestos)
            is_valid_type, discard_reason, discard_detail = self.verify_product_type_integrity(prod, criteria)
            if not is_valid_type:
                self._record_discard(
                    prod,
                    discard_reason or DiscardReason.COMPONENT_OR_SPARE_PART,
                    discard_detail or "Componente o accesorio incompatible con el tipo de equipo solicitado"
                )
                continue

            # 5. Control de sensatez de precio vs hardware (CPUs de gama alta no pueden valer < 400€)
            m_high_cpu = re.search(self.HIGH_END_CPU_PATTERN, title_upper)
            if m_high_cpu:
                if prod.price > 0 and prod.price < 400.0:
                    self._record_discard(
                        prod,
                        DiscardReason.UNREASONABLE_PRICE,
                        f"CPU de gama alta ({m_high_cpu.group(1)}) con precio anormalmente bajo ({prod.price:.2f} € < 400 €)"
                    )
                    continue

            # 5b. Control de sensatez de precio mínimo para equipos informáticos completos (mini PC, portátil, sobremesa)
            if criteria.product_type in ["mini_pc", "laptop", "desktop"] or (
                criteria.category in [ProductCategory.PC_COMPONENTS, ProductCategory.LAPTOPS]
                and any(w in criteria.clean_query.lower() for w in ["mini pc", "portatil", "laptop", "sobremesa", "ordenador"])
            ):
                min_system = criteria.min_system_price or 35.0
                if prod.price > 0 and prod.price < min_system:
                    self._record_discard(
                        prod,
                        DiscardReason.UNREASONABLE_PRICE,
                        f"Precio ({prod.price:.2f} €) inviable para un ordenador completo (< {min_system:.2f} €)"
                    )
                    continue

            # 6. Política de Coincidencia de Modelo (Token Match Obligatorio)
            target_models = criteria.target_models or ([criteria.target_model] if criteria.target_model else [])
            if target_models:
                variants = criteria.target_model_variants or target_models
                matches_model = any(
                    re.search(rf"(?<![a-z0-9]){re.escape(v.lower())}(?![a-z0-9])", f" {title_lower} ")
                    for v in variants
                )
                if not matches_model:
                    models_str = ", ".join(target_models)
                    self._record_discard(
                        prod,
                        DiscardReason.TARGET_MODEL_MISMATCH,
                        f"No incluye ninguno de los modelos solicitados ({models_str})"
                    )
                    continue

            # 6b. Control de coherencia de marca solicitada
            if criteria.target_brand:
                brand_norm = criteria.target_brand.lower()
                major_it_brands = {
                    "hp", "lenovo", "dell", "apple", "asus", "acer", "msi", "samsung",
                    "huawei", "chuwi", "beelink", "gmktec", "trigkey", "minisforum",
                    "geekom", "acemagic", "bmax", "ouvis", "kamrui", "mllse", "soyo",
                    "firebat", "genmachine", "topton", "mele", "chatreey", "morefine", "szbox",
                    "ledkia", "osram", "velamp"
                }
                conflicting_brands = [b for b in major_it_brands if b != brand_norm]

                brand_aliases = {brand_norm}
                if brand_norm == "gmktec":
                    brand_aliases.add("gmk")

                has_target_brand = any(re.search(rf"\b{re.escape(b)}\b", title_lower) for b in brand_aliases)

                detected_other_brand = next(
                    (b for b in conflicting_brands if re.search(rf"\b{re.escape(b)}\b", title_lower)),
                    None
                )
                if detected_other_brand and not has_target_brand:
                    self._record_discard(
                        prod,
                        DiscardReason.BRAND_MISMATCH,
                        f"Marca incompatible ({detected_other_brand.upper()}) detectada en lugar de {criteria.target_brand}"
                    )
                    continue

                if not has_target_brand:
                    self._record_discard(
                        prod,
                        DiscardReason.BRAND_MISMATCH,
                        f"No incluye la marca solicitada ({criteria.target_brand})"
                    )
                    continue

            # 7. Filtro de palabras excluidas (palabras completas)
            matched_exclude = next((ex for ex in criteria.exclude_keywords if re.search(rf"\b{re.escape(ex.lower())}\b", title_lower)), None)
            if matched_exclude:
                self._record_discard(
                    prod,
                    DiscardReason.EXCLUDED_KEYWORD,
                    f"Contiene palabra expresamente excluida: '{matched_exclude}'"
                )
                continue

            # 8. Exclusión de procesadores Intel Core de generaciones antiguas (<= 11)
            old_core = re.search(r"\bI[3579]-?(?:[1-9]\d{2}|[2-9]\d{3}|1[01]\d{2,3})(?:G\d|[A-Z])*\b", title_upper)
            if old_core:
                matched_allowed = any(re.search(rf"\b{re.escape(c.upper())}\b", title_upper) for c in criteria.allowed_cpus)
                if not matched_allowed:
                    self._record_discard(
                        prod,
                        DiscardReason.OLD_INTEL_CORE,
                        f"Procesador Intel Core antiguo detectado ({old_core.group(0)}, generación <= 11ª)"
                    )
                    continue

            # 9. Filtro estricto de procesadores permitidos
            detected_cpu = None
            if criteria.allowed_cpus:
                matched_cpus = [c for c in criteria.allowed_cpus if re.search(rf"\b{re.escape(c.upper())}\b", title_upper)]
                if not matched_cpus:
                    cpus_str = ", ".join(criteria.allowed_cpus)
                    self._record_discard(
                        prod,
                        DiscardReason.DISALLOWED_CPU,
                        f"No incluye procesador permitido ({cpus_str})"
                    )
                    continue
                detected_cpu = matched_cpus[0]

            # 10. Filtro de memoria RAM mínima
            if criteria.min_ram_gb:
                if "BAREBONE" in title_upper or "SIN RAM" in title_upper:
                    self._record_discard(prod, DiscardReason.INSUFFICIENT_RAM, "Configuración barebone o sin memoria RAM")
                    continue
                ram_matches = re.findall(r"\b(\d{1,2})\s*GB\s*(?:DDR\d\s*)?RAM\b", title_upper)
                if not ram_matches:
                    ram_matches = re.findall(r"\b(\d{1,2})\s*G\s*RAM\b", title_upper)
                if not ram_matches:
                    comb = re.findall(r"\b(\d{1,2})\s*GB\s*(?:[+/]|DDR\d)", title_upper)
                    if comb:
                        ram_matches = comb
                if ram_matches:
                    max_found_ram = max(int(r) for r in ram_matches)
                    if max_found_ram < criteria.min_ram_gb:
                        self._record_discard(
                            prod,
                            DiscardReason.INSUFFICIENT_RAM,
                            f"Memoria RAM ({max_found_ram} GB) inferior a los {criteria.min_ram_gb} GB requeridos"
                        )
                        continue

            # 11. Filtro de almacenamiento SSD mínimo
            if criteria.min_storage_gb:
                if "BAREBONE" in title_upper or "SIN DISCO" in title_upper or "SIN SSD" in title_upper:
                    self._record_discard(prod, DiscardReason.INSUFFICIENT_STORAGE, "Configuración barebone o sin disco SSD")
                    continue
                has_tb = bool(re.search(r"\b\d\s*TB\b", title_upper))
                if not has_tb:
                    disk_matches = re.findall(r"\b(\d{2,4})\s*GB\s*(?:SSD|ROM|DISCO|EMMC|NVME|M\.2|PCIE)\b", title_upper)
                    if not disk_matches:
                        disk_matches = re.findall(r"(?:[+/]|\b(?:CON|DE)\s*)(\d{3,4})\s*GB\b", title_upper)
                    if disk_matches:
                        max_found_disk = max(int(d) for d in disk_matches)
                        if max_found_disk >= 64 and max_found_disk < criteria.min_storage_gb:
                            self._record_discard(
                                prod,
                                DiscardReason.INSUFFICIENT_STORAGE,
                                f"Almacenamiento SSD ({max_found_disk} GB) inferior a los {criteria.min_storage_gb} GB requeridos"
                            )
                            continue

            # 12. Descartar precio desconocido si se fijó presupuesto
            if (criteria.max_price or criteria.max_price_by_cpu) and prod.price <= 0.0:
                self._record_discard(
                    prod,
                    DiscardReason.UNKNOWN_PRICE_WITH_BUDGET,
                    "Precio no publicado o 0.00 € con presupuesto fijado"
                )
                continue

            # 13. Filtro de precios condicionales por CPU
            if criteria.max_price_by_cpu and detected_cpu:
                exceeded_cpu_price = False
                exceeded_detail = ""
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.upper() in detected_cpu.upper() or detected_cpu.upper() in cpu_key.upper():
                        if prod.price > p_max:
                            exceeded_cpu_price = True
                            exceeded_detail = f"Precio ({prod.price:.2f} €) excede el límite fijado para CPU {cpu_key} ({p_max:.2f} €)"
                            break
                if exceeded_cpu_price:
                    self._record_discard(prod, DiscardReason.CPU_MAX_PRICE_EXCEEDED, exceeded_detail)
                    continue

            # 14. Filtro de stock
            if criteria.in_stock_only and not prod.in_stock:
                self._record_discard(prod, DiscardReason.OUT_OF_STOCK, "Artículo sin stock inmediato disponible")
                continue

            # 15. Filtro de envío local
            if criteria.ships_from_spain_only and not prod.ships_from_spain:
                self._record_discard(prod, DiscardReason.NON_LOCAL_SHIPPING, "Envío no garantizado desde España o almacén europeo")
                continue

            # 16. Filtro de precio máximo general
            if criteria.max_price and prod.price > criteria.max_price:
                self._record_discard(
                    prod,
                    DiscardReason.PRICE_ABOVE_MAX,
                    f"Precio ({prod.price:.2f} €) supera el presupuesto máximo ({criteria.max_price:.2f} €)"
                )
                continue

            # 17. Filtro de precio mínimo general
            if criteria.min_price and prod.price < criteria.min_price:
                self._record_discard(
                    prod,
                    DiscardReason.PRICE_BELOW_MIN,
                    f"Precio ({prod.price:.2f} €) inferior al mínimo fijado ({criteria.min_price:.2f} €)"
                )
                continue

            # 18. Calcular score de afinidad
            prod.match_score = self.calculate_match_score(prod, criteria)

            # 19. Umbral de corte de afinidad mínimo (mínimo 80%)
            if prod.match_score < criteria.min_score_threshold:
                self._record_discard(
                    prod,
                    DiscardReason.AFFINITY_THRESHOLD,
                    f"Puntuación de afinidad ({prod.match_score:.1f}%) inferior al corte mínimo ({criteria.min_score_threshold:.1f}%)"
                )
                continue

            filtered.append(prod)

        # Ordenación
        if criteria.sort_by == "price_asc":
            filtered.sort(key=lambda p: p.price)
        elif criteria.sort_by == "price_desc":
            filtered.sort(key=lambda p: p.price, reverse=True)
        else:
            # Por defecto: relevancia (match_score descendente, y luego precio ascendente)
            filtered.sort(key=lambda p: (-p.match_score, p.price))

        return filtered
