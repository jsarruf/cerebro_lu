import unittest

from cerebro_lu.repository import InMemorySalesRepository
from cerebro_lu.services import SalesService


class SalesServiceTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemorySalesRepository()
        self.service = SalesService(
            self.repository,
            status_selector=lambda _: "Enviado",
        )

    def test_add_product_normalizes_name_and_accumulates_quantity(self):
        first = self.service.add_product("session-1", "  Tenis Azul! ", 2)
        second = self.service.add_product("session-1", "tenis azul", 1)

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertEqual(second["cart"], {"tenis azul": 3})
        self.assertEqual(second["total_items"], 3)

    def test_add_rejects_empty_product_and_non_positive_quantity(self):
        empty = self.service.add_product("session-1", "  ", 1)
        zero = self.service.add_product("session-1", "tenis", 0)
        negative = self.service.add_product("session-1", "tenis", -2)

        self.assertFalse(empty["ok"])
        self.assertFalse(zero["ok"])
        self.assertFalse(negative["ok"])
        self.assertEqual(self.service.get_cart("session-1")["cart"], {})

    def test_add_rejects_excessive_quantity_and_product_name(self):
        quantity = self.service.add_product("session-1", "tenis", 1_001)
        product = self.service.add_product("session-1", "x" * 201, 1)

        self.assertFalse(quantity["ok"])
        self.assertFalse(product["ok"])

    def test_invalid_session_is_rejected(self):
        add = self.service.add_product(" ", "tenis", 1)
        cart = self.service.get_cart("")
        checkout = self.service.checkout_pix(" ")

        self.assertEqual(add["message"], "Session ID invalido.")
        self.assertEqual(cart["message"], "Session ID invalido.")
        self.assertEqual(checkout["message"], "Session ID invalido.")

    def test_remove_supports_partial_product_name(self):
        self.service.add_product("session-1", "tenis de corrida azul", 1)

        result = self.service.remove_product("session-1", "tenis de corrida")

        self.assertTrue(result["ok"])
        self.assertEqual(result["cart"], {})

    def test_remove_unknown_product_keeps_cart(self):
        self.service.add_product("session-1", "tenis", 1)

        result = self.service.remove_product("session-1", "mochila")

        self.assertFalse(result["ok"])
        self.assertEqual(result["cart"], {"tenis": 1})

    def test_empty_checkout_returns_safe_error(self):
        result = self.service.checkout_pix("session-1")

        self.assertFalse(result["ok"])
        self.assertIn("carrinho esta vazio", result["message"])

    def test_checkout_creates_order_clears_cart_and_returns_status(self):
        self.service.add_product("session-1", "notebook", 1)

        checkout = self.service.checkout_pix("session-1")
        status = self.service.get_order_status(checkout["order_id"])

        self.assertTrue(checkout["ok"])
        self.assertRegex(checkout["order_id"], r"PED-\d{8}-[0-9A-F]{6}")
        self.assertTrue(checkout["pix_code"].startswith("000201"))
        self.assertEqual(self.service.get_cart("session-1")["cart"], {})
        self.assertEqual(status["status"], "Enviado")

    def test_unknown_order_is_not_found(self):
        result = self.service.get_order_status("PED-20260727-FFFFFF")

        self.assertEqual(
            result,
            {"ok": False, "message": "Pedido nao encontrado."},
        )

    def test_history_persists_both_roles_in_order(self):
        self.service.record_message("session-1", "user", "ola")
        self.service.record_message("session-1", "assistant", "oi")

        history = self.service.get_history("session-1")

        self.assertEqual([message.role for message in history], ["user", "assistant"])
        self.assertEqual([message.content for message in history], ["ola", "oi"])
        self.assertEqual(self.service.get_history("session-2"), ())


if __name__ == "__main__":
    unittest.main()
