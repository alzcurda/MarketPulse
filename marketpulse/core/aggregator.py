import re
import unicodedata
from typing import List
from marketpulse.models import ProductCategory, ProductResult, SearchCriteria


class Aggregator:
    """
    Agregador y motor de ranking.
    Recibe los resultados de las tiendas consultadas, filtra por restricciones,
    calcula la puntuación de afinidad y ordena los productos para la comparativa.
    """

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
        r"\brobot\s+aspirador\b",
        r"\bbatidora\b",
        r"\btostador[a]?\b",
        r"\bplancha\b",
        r"\bcalefactor\b",
        r"\baire\s+acondicionado\b",
        r"\bhumidificador\b",
        r"\bdeshumidificador\b",
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
    ]

    # Accesorios que saturan las búsquedas de ordenadores/mini PCs
    ACCESSORY_PATTERNS = [
        r"\bdock(?:ing)?(?:\s+station)?\b",
        r"\bestaci[oó]n\s+de\s+acoplamiento\b",
        r"\bcarcasa(?:\s+vac[ií]a)?\b",
        r"\bcaja\s+vac[ií]a\b",
        r"\bsolo\s+caja\b",
        r"\bsoporte\s+vesa\b",
        r"\badaptador\s+vesa\b",
        r"\bfunda\b",
        r"\bcable\b",
        r"\balimentador\b",
        r"\bcargador\b",
        r"\bpegatina\b",
        r"\bvinilo\b",
        r"\bprotector\b",
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
        if criteria.target_model:
            variants = criteria.target_model_variants or [criteria.target_model]
            model_matched = False
            for v in variants:
                v_norm = self._strip_accents(v)
                if re.search(rf"(?<![a-z0-9]){re.escape(v_norm)}(?![a-z0-9])", f" {title_norm} "):
                    model_matched = True
                    break
            if model_matched:
                score += 35.0
                matched_specs.append(criteria.target_model)
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

    def filter_and_rank(self, raw_results: List[ProductResult], criteria: SearchCriteria) -> List[ProductResult]:
        """
        Aplica filtros y ordena los resultados de múltiples tiendas según reglas estrictas:
        - Coincidencia obligatoria de token de modelo
        - Aislamiento estricto de categoría (no electrodomésticos ni no-IT)
        - Control de sensatez precio vs hardware (Core Ultra/i9/Ryzen 9 >= 400€, no docks)
        - Umbral de afinidad mínima (score >= 80%)
        """
        filtered: List[ProductResult] = []
        seen_urls = set()

        for prod in raw_results:
            # 1. Deduplicación por URL
            if prod.url in seen_urls:
                continue
            seen_urls.add(prod.url)

            # 2. Descartar enlaces a páginas de búsqueda o títulos ficticios
            url_lower = prod.url.lower()
            if any(p in url_lower for p in ["/s?k=", "/w/wholesale-", "/buscar/?query=", "/search.html?query="]):
                continue
            if prod.title.startswith("Resultados ") or prod.title.startswith("[Acceso directo"):
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
                if any(re.search(pat, title_lower) for pat in self.NON_COMPUTING_PATTERNS):
                    continue

            # 4. Filtrar accesorios (docks, carcasas, soportes vesa, fundas, cables)
            query_has_accessory = any(re.search(pat, criteria.clean_query.lower()) for pat in self.ACCESSORY_PATTERNS)
            if not query_has_accessory:
                if any(re.search(pat, title_lower) for pat in self.ACCESSORY_PATTERNS):
                    continue

            # 5. Control de sensatez de precio vs hardware (CPUs de gama alta no pueden valer < 400€)
            if re.search(self.HIGH_END_CPU_PATTERN, title_upper):
                if prod.price > 0 and prod.price < 400.0:
                    continue

            # 6. Política de Coincidencia de Modelo (Token Match Obligatorio)
            if criteria.target_model:
                variants = criteria.target_model_variants or [criteria.target_model]
                matches_model = any(
                    re.search(rf"(?<![a-z0-9]){re.escape(v.lower())}(?![a-z0-9])", f" {title_lower} ")
                    for v in variants
                )
                if not matches_model:
                    continue

            # 7. Filtro de palabras excluidas (palabras completas)
            if any(re.search(rf"\b{re.escape(ex.lower())}\b", title_lower) for ex in criteria.exclude_keywords):
                continue

            # 8. Exclusión de procesadores Intel Core de generaciones antiguas (<= 11)
            old_core = re.search(r"\bI[3579]-?(?:[1-9]\d{2}|[2-9]\d{3}|1[01]\d{2,3})(?:G\d|[A-Z])*\b", title_upper)
            if old_core:
                matched_allowed = any(re.search(rf"\b{re.escape(c.upper())}\b", title_upper) for c in criteria.allowed_cpus)
                if not matched_allowed:
                    continue

            # 9. Filtro estricto de procesadores permitidos
            detected_cpu = None
            if criteria.allowed_cpus:
                matched_cpus = [c for c in criteria.allowed_cpus if re.search(rf"\b{re.escape(c.upper())}\b", title_upper)]
                if not matched_cpus:
                    continue
                detected_cpu = matched_cpus[0]

            # 10. Filtro de memoria RAM mínima
            if criteria.min_ram_gb:
                if "BAREBONE" in title_upper or "SIN RAM" in title_upper:
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
                        continue

            # 11. Filtro de almacenamiento SSD mínimo
            if criteria.min_storage_gb:
                if "BAREBONE" in title_upper or "SIN DISCO" in title_upper or "SIN SSD" in title_upper:
                    continue
                has_tb = bool(re.search(r"\b\d\s*TB\b", title_upper))
                if not has_tb:
                    disk_matches = re.findall(r"\b(\d{2,4})\s*GB\s*(?:SSD|ROM|DISCO|EMMC|NVME|M\.2|PCIE)\b", title_upper)
                    if not disk_matches:
                        disk_matches = re.findall(r"(?:[+/]|\b(?:CON|DE)\s*)(\d{3,4})\s*GB\b", title_upper)
                    if disk_matches:
                        max_found_disk = max(int(d) for d in disk_matches)
                        if max_found_disk >= 64 and max_found_disk < criteria.min_storage_gb:
                            continue

            # 12. Descartar precio desconocido si se fijó presupuesto
            if (criteria.max_price or criteria.max_price_by_cpu) and prod.price <= 0.0:
                continue

            # 13. Filtro de precios condicionales por CPU
            if criteria.max_price_by_cpu and detected_cpu:
                exceeded_cpu_price = False
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.upper() in detected_cpu.upper() or detected_cpu.upper() in cpu_key.upper():
                        if prod.price > p_max:
                            exceeded_cpu_price = True
                            break
                if exceeded_cpu_price:
                    continue

            # 14. Filtro de stock
            if criteria.in_stock_only and not prod.in_stock:
                continue

            # 15. Filtro de envío local
            if criteria.ships_from_spain_only and not prod.ships_from_spain:
                continue

            # 16. Filtro de precio máximo general
            if criteria.max_price and prod.price > criteria.max_price:
                continue

            # 17. Filtro de precio mínimo general
            if criteria.min_price and prod.price < criteria.min_price:
                continue

            # 18. Calcular score de afinidad
            prod.match_score = self.calculate_match_score(prod, criteria)

            # 19. Umbral de corte de afinidad mínimo (mínimo 80%)
            if prod.match_score < criteria.min_score_threshold:
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
