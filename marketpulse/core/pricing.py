import re
from typing import Optional, Tuple
from bs4 import Tag


def parse_price(raw_text: str) -> Optional[float]:
    """
    Normalización y Parseo Numérico Universal de Precios.
    Gestiona formatos europeos (1.139,00 €) y anglosajones ($1,139.00),
    así como estructuras HTML truncadas o limpias.
    """
    if not raw_text:
        return None

    # Si contiene indicadores de rango (ej. '113,00 € - 212,12 €'), tomar el precio inicial
    if " - " in raw_text or " a " in raw_text:
        parts = re.split(r"\s+[-–—]\s+|\s+a\s+", raw_text)
        if parts:
            p_first = parse_price(parts[0])
            if p_first is not None:
                return p_first

    # 1. Conservar solo dígitos, comas y puntos
    cleaned = re.sub(r"[^\d.,]", "", raw_text.strip())
    if not cleaned:
        return None

    # 2. Ambos separadores presentes
    if "." in cleaned and "," in cleaned:
        if cleaned.rfind(".") > cleaned.rfind(","):
            # Formato Anglo: 1,139.00 -> quitar comas
            cleaned = cleaned.replace(",", "")
        else:
            # Formato Europeo: 1.139,00 -> quitar puntos, cambiar coma por punto
            cleaned = cleaned.replace(".", "").replace(",", ".")

    # 3. Solo coma presente
    elif "," in cleaned:
        parts = cleaned.split(",")
        if len(parts[-1]) == 2:  # Decimal (ej. 199,99)
            cleaned = cleaned.replace(",", ".")
        else:  # Miles sin decimales (ej. 1,000)
            cleaned = cleaned.replace(",", "")

    # 4. Solo punto presente
    elif "." in cleaned:
        parts = cleaned.split(".")
        if len(parts[-1]) == 3 and len(parts) > 1:  # Miles (ej. 1.139)
            cleaned = cleaned.replace(".", "")
        # Si tiene 2 dígitos (ej. 199.99), float() ya lo interpreta bien

    try:
        return float(cleaned)
    except ValueError:
        return None


def parse_price_range(raw_text: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Detecta y parsea un rango de precios (ej: '113 € - 1.139 €').
    Devuelve (min_price, max_price). Si no es un rango, min_price == max_price.
    """
    if not raw_text:
        return None, None

    if " - " in raw_text or " a " in raw_text:
        parts = re.split(r"\s+[-–—]\s+|\s+a\s+", raw_text)
        if len(parts) >= 2:
            p1 = parse_price(parts[0])
            p2 = parse_price(parts[1])
            return p1, p2

    p = parse_price(raw_text)
    return p, p


def is_financing_or_unit_price(text: str) -> bool:
    """
    Detecta si una cadena de texto de precio corresponde a cuotas de financiación,
    pago aplazado o precios por unidad (/mes, /cuota, /kg, etc.).
    """
    if not text:
        return False

    text_clean = re.sub(r"\s+", " ", text.lower())
    financing_patterns = [
        r"/\s*(?:mes|cuota|kg|ud|unidad|litro|m2|hora)\b",
        r"\bal\s+mes\b",
        r"\bcuotas?\b",
        r"\bpaga\s+en\b",
        r"\bmeses\s+sin\s+intereses\b",
        r"\bfinancia",
        r"\bcofidis\b",
        r"\bopenbank\b",
        r"\bklarna\b",
        r"\bsequra\b",
        r"\bpaga\s+despu[eé]s\b",
    ]

    return any(re.search(pat, text_clean) for pat in financing_patterns)


def is_strikethrough_or_old_price(elem: Tag) -> bool:
    """
    Comprueba si un elemento HTML contiene un precio tachado, antiguo o PVP original,
    evitando que se capture en lugar del precio de oferta activo.
    """
    if not elem:
        return False

    if elem.name in ["del", "s", "strike"]:
        return True

    classes = elem.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
    else:
        class_str = str(classes).lower()

    strike_classes = [
        "a-text-price",
        "strike",
        "strikethrough",
        "line-through",
        "original-price",
        "old-price",
        "regular-price",
        "c-product-card__price-strikethrough",
        "price-strikethrough",
    ]

    if any(sc in class_str for sc in strike_classes):
        return True

    style = elem.get("style", "").lower()
    if "line-through" in style:
        return True

    return False


def is_sponsored_card(elem: Tag, url: str = "") -> bool:
    """
    Detecta si una tarjeta de producto o URL corresponde a un producto patrocinado / publicidad.
    """
    if url:
        url_lower = url.lower()
        if any(sp in url_lower for sp in ["&sprefix=", "/gp/slredirect/", "sspa/click", "sponsored=true"]):
            return True

    if not elem:
        return False

    classes = elem.get("class", [])
    if isinstance(classes, list):
        class_str = " ".join(classes).lower()
    else:
        class_str = str(classes).lower()

    if any(c in class_str for c in ["sponsored", "ad-container", "ad-item", "sp-sponsored-result"]):
        return True

    sponsored_tags = elem.select(".s-sponsored-label, .s-sponsored-info-icon, [data-component-type='sp-sponsored-result']")
    if sponsored_tags:
        return True

    for s in elem.stripped_strings:
        if s.strip().lower() in ["patrocinado", "sponsored", "anuncio", "publicidad"]:
            return True

    return False


def is_out_of_stock(elem: Tag) -> bool:
    """
    Verifica si una tarjeta o ficha marca el producto como agotado o no disponible.
    """
    if not elem:
        return False

    text = elem.get_text(separator=" ").lower()
    out_of_stock_phrases = [
        "actualmente no disponible",
        "no disponible temporalmente",
        "agotado",
        "sin stock",
        "fuera de stock",
        "out of stock",
        "temporarily out of stock",
    ]

    return any(phrase in text for phrase in out_of_stock_phrases)
