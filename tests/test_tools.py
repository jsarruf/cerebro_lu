import unittest

from cerebro_lu import tools


class ToolsTest(unittest.TestCase):
    def setUp(self):
        tools.store.reset()

    def test_add_and_get_cart_delegate_to_sales_service(self):
        added = tools.add_product("session-1", "monitor", 2)
        cart = tools.get_cart("session-1")

        self.assertTrue(added["ok"])
        self.assertEqual(cart["cart"], {"monitor": 2})

    def test_direct_tool_calls_return_safe_validation_errors(self):
        invalid_quantity = tools.add_product("session-1", "monitor", 0)
        invalid_product = tools.add_product("session-1", "", 1)
        invalid_session = tools.get_cart(" ")

        self.assertFalse(invalid_quantity["ok"])
        self.assertFalse(invalid_product["ok"])
        self.assertEqual(invalid_session["message"], "Session ID invalido.")

    def test_checkout_and_status_tools_share_repository(self):
        tools.add_product("session-1", "teclado", 1)
        checkout = tools.checkout_pix("session-1")
        status = tools.get_order_status(checkout["order_id"])

        self.assertTrue(checkout["ok"])
        self.assertTrue(status["ok"])


if __name__ == "__main__":
    unittest.main()
