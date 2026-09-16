import re
from typing import List
from marketpulse.models import ProductResult, SearchCriteria


class Aggregator:
    """
    Agregador y motor de ranking.
    Recibe los resultados de las tiendas consultadas, filtra por restricciones,
    calcula la puntuación de afinidad y ordena los productos para la comparativa.
    """

    def calculate_match_score(self, product: ProductResult, criteria: SearchCriteria) -> float:
        """
        Calcula una puntuación de afinidad (0 a 100) en base a la coincidencia con
        las especificaciones deseadas y el término de búsqueda.
        """
        score = 50.0
        title_lower = product.title.lower()
        matched_specs = []

        # 1. Coincidencia con palabras de la búsqueda limpia
        query_words = criteria.clean_query.lower().split()
        for word in query_words:
            if len(word) > 2 and word in title_lower:
                score += (25.0 / max(len(query_words), 1))

        # 2. Coincidencia con especificaciones técnicas clave
        for spec in criteria.key_specs:
            spec_clean = spec.lower().replace(" ", "")
            if spec.lower() in title_lower or spec_clean in title_lower.replace(" ", ""):
                score += 15.0
                matched_specs.append(spec)

        product.matched_specs = matched_specs

        # 3. Bonus por descuento activo
        if product.discount_percentage and product.discount_percentage > 5:
            score += min(product.discount_percentage * 0.5, 10.0)

        # 4. Comprobación de presupuesto
        if criteria.max_price and product.price > criteria.max_price:
            score -= 30.0

        return max(0.0, min(100.0, round(score, 1)))

    def filter_and_rank(self, raw_results: List[ProductResult], criteria: SearchCriteria) -> List[ProductResult]:
        """
        Aplica filtros y ordena los resultados de múltiples tiendas.
        """
        filtered: List[ProductResult] = []
        seen_urls = set()

        # Palabras de descarte habituales si buscamos equipos completos (evita accesorios que saturan búsquedas)
        accessory_words = ["funda", "cable", "adaptador", "pegatina", "vinilo", "protector"]

        for prod in raw_results:
            # Deduplicación por URL
            if prod.url in seen_urls:
                continue
            seen_urls.add(prod.url)

            # Descartar enlaces que apunten a páginas de búsqueda o títulos ficticios
            url_lower = prod.url.lower()
            if any(p in url_lower for p in ["/s?k=", "/w/wholesale-", "/buscar/?query=", "/search.html?query="]):
                continue
            if prod.title.startswith("Resultados ") or prod.title.startswith("[Acceso directo"):
                continue

            title_lower = prod.title.lower()

            # Filtrar accesorios si no se pidieron explícitamente
            if not any(acc in criteria.clean_query.lower() for acc in accessory_words):
                if any(re.search(rf"\b{acc}\b", title_lower) for acc in accessory_words):
                    continue

            # Filtro de palabras excluidas (palabras completas)
            if any(re.search(rf"\b{re.escape(ex.lower())}\b", title_lower) for ex in criteria.exclude_keywords):
                continue

            title_upper = prod.title.upper()

            # Exclusión de procesadores Intel Core de generaciones antiguas (<= 11)
            old_core = re.search(r"\bI[3579]-?(?:[1-9]\d{2,3}|1[01]\d{3})[A-Z0-9]*\b", title_upper)
            if old_core:
                matched_allowed = any(re.search(rf"\b{re.escape(c.upper())}\b", title_upper) for c in criteria.allowed_cpus)
                if not matched_allowed:
                    continue

            # Filtro estricto de procesadores permitidos
            detected_cpu = None
            if criteria.allowed_cpus:
                matched_cpus = [c for c in criteria.allowed_cpus if re.search(rf"\b{re.escape(c.upper())}\b", title_upper)]
                if not matched_cpus:
                    continue
                detected_cpu = matched_cpus[0]

            # Filtro de memoria RAM mínima
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

            # Filtro de almacenamiento SSD mínimo
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

            # Si el usuario ha fijado un presupuesto (general o condicional por CPU),
            # descartamos artículos con precio desconocido (0.0 / "Ver en tienda")
            # para evitar colar productos de 500€-600€ que violan el presupuesto del usuario.
            if (criteria.max_price or criteria.max_price_by_cpu) and prod.price <= 0.0:
                continue

            # Filtro de precios condicionales por CPU
            if criteria.max_price_by_cpu and detected_cpu:
                exceeded_cpu_price = False
                for cpu_key, p_max in criteria.max_price_by_cpu.items():
                    if cpu_key.upper() in detected_cpu.upper() or detected_cpu.upper() in cpu_key.upper():
                        if prod.price > p_max:
                            exceeded_cpu_price = True
                            break
                if exceeded_cpu_price:
                    continue

            # Filtro de stock
            if criteria.in_stock_only and not prod.in_stock:
                continue

            # Filtro de envío local
            if criteria.ships_from_spain_only and not prod.ships_from_spain:
                continue

            # Filtro de precio máximo general
            if criteria.max_price and prod.price > criteria.max_price:
                continue

            # Filtro de precio mínimo general
            if criteria.min_price and prod.price < criteria.min_price:
                continue

            # Calcular score
            prod.match_score = self.calculate_match_score(prod, criteria)
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
