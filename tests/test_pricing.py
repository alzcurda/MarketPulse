import unittest
from bs4 import BeautifulSoup
from marketpulse.core.pricing import (
    parse_price,
    parse_price_range,
    is_financing_or_unit_price,
    is_strikethrough_or_old_price,
    is_sponsored_card,
    is_out_of_stock,
)


class TestPricingModule(unittest.TestCase):

    def test_parse_price_european_format(self):
        self.assertEqual(parse_price("1.139,00 €"), 1139.00)
        self.assertEqual(parse_price("212,12€"), 212.12)
        self.assertEqual(parse_price("1.000,50"), 1000.50)
        self.assertEqual(parse_price("199,99 €"), 199.99)
        self.assertEqual(parse_price("12,50 €"), 12.50)

    def test_parse_price_anglo_format(self):
        self.assertEqual(parse_price("$1,139.00"), 1139.00)
        self.assertEqual(parse_price("1,250.50"), 1250.50)
        self.assertEqual(parse_price("$199.99"), 199.99)
        self.assertEqual(parse_price("12.50"), 12.50)

    def test_parse_price_single_separator(self):
        # Coma con 2 dígitos al final -> decimal
        self.assertEqual(parse_price("199,99"), 199.99)
        # Coma con 3 dígitos al final -> miles
        self.assertEqual(parse_price("1,000"), 1000.0)
        # Punto con 3 dígitos al final (y más de una parte) -> miles
        self.assertEqual(parse_price("1.139"), 1139.0)
        # Punto con 2 dígitos al final -> decimal
        self.assertEqual(parse_price("199.99"), 199.99)

    def test_parse_price_range(self):
        min_p, max_p = parse_price_range("113,00 € - 1.139,00 €")
        self.assertEqual(min_p, 113.0)
        self.assertEqual(max_p, 1139.0)

        # parse_price en rango devuelve el precio base inicial
        self.assertEqual(parse_price("113,00 € - 1.139,00 €"), 113.0)

    def test_invalid_and_empty_prices(self):
        self.assertIsNone(parse_price(""))
        self.assertIsNone(parse_price(None))
        self.assertIsNone(parse_price("Ver en tienda"))
        self.assertIsNone(parse_price("Consultar disponibilidad"))

    def test_is_financing_or_unit_price(self):
        self.assertTrue(is_financing_or_unit_price("14,13 € / mes"))
        self.assertTrue(is_financing_or_unit_price("19,99 €/mes con Cofidis"))
        self.assertTrue(is_financing_or_unit_price("Desde 25 € al mes"))
        self.assertTrue(is_financing_or_unit_price("Cuotas de 30 €"))
        self.assertTrue(is_financing_or_unit_price("Paga en 3 cuotas con Klarna"))
        self.assertTrue(is_financing_or_unit_price("3,50 € / kg"))
        self.assertFalse(is_financing_or_unit_price("212,12 €"))
        self.assertFalse(is_financing_or_unit_price("199,99 € (IVA incluido)"))

    def test_is_strikethrough_or_old_price(self):
        soup = BeautifulSoup("""
            <div>
                <span class="a-price a-text-price"><span class="a-offscreen">299,00 €</span></span>
                <del>350,00 €</del>
                <span class="regular-price">400,00 €</span>
                <span class="c-product-card__price-current">212,12 €</span>
            </div>
        """, "html.parser")

        text_price = soup.select_one(".a-text-price")
        del_elem = soup.find("del")
        reg_price = soup.select_one(".regular-price")
        curr_price = soup.select_one(".c-product-card__price-current")

        self.assertTrue(is_strikethrough_or_old_price(text_price))
        self.assertTrue(is_strikethrough_or_old_price(del_elem))
        self.assertTrue(is_strikethrough_or_old_price(reg_price))
        self.assertFalse(is_strikethrough_or_old_price(curr_price))

    def test_is_sponsored_card(self):
        soup = BeautifulSoup("""
            <div class="s-result-item">
                <span class="s-sponsored-label">Patrocinado</span>
                <h2>Producto Patrocinado</h2>
            </div>
        """, "html.parser")
        card_sponsored = soup.select_one(".s-result-item")
        self.assertTrue(is_sponsored_card(card_sponsored))
        self.assertTrue(is_sponsored_card(None, url="https://amazon.es/gp/slredirect/picador"))

        soup_organic = BeautifulSoup("""
            <div class="s-result-item">
                <h2>Producto Orgánico Normal</h2>
            </div>
        """, "html.parser")
        card_organic = soup_organic.select_one(".s-result-item")
        self.assertFalse(is_sponsored_card(card_organic, url="https://amazon.es/dp/B012345"))

    def test_is_out_of_stock(self):
        soup_oos = BeautifulSoup("<div><h3>Portátil</h3><span>Actualmente no disponible.</span></div>", "html.parser")
        self.assertTrue(is_out_of_stock(soup_oos))

        soup_in_stock = BeautifulSoup("<div><h3>Portátil</h3><span>En stock. Envío gratis</span></div>", "html.parser")
        self.assertFalse(is_out_of_stock(soup_in_stock))


if __name__ == "__main__":
    unittest.main()
