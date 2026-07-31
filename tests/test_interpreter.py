import re
import unittest

from cerebro_lu import interpreter
from cerebro_lu.tools import store


class InterpreterTest(unittest.TestCase):
    def setUp(self):
        store.reset()

    def test_add_product_persists_by_session(self):
        response = interpreter.reply(
            "session-1",
            "Quero adicionar 2 tenis de corrida ao meu carrinho.",
        )

        self.assertIn("Adicionei 2 tenis de corrida", response)
        self.assertEqual(store.get_cart("session-1")["cart"], {"tenis de corrida": 2})
        self.assertEqual(store.get_cart("session-2")["cart"], {})

    def test_imperative_add_keeps_previous_cart_items(self):
        interpreter.reply(
            "session-1",
            "Quero adicionar 2 tenis de corrida ao meu carrinho.",
        )
        add_bag = interpreter.reply(
            "session-1",
            "Adicione uma bolsa preta ao carrinho.",
        )
        cart = interpreter.reply("session-1", "O que tem no meu carrinho?")

        self.assertIn("Adicionei 1 bolsa preta", add_bag)
        self.assertIn("2x tenis de corrida", cart)
        self.assertIn("1x bolsa preta", cart)
        self.assertEqual(
            store.get_cart("session-1")["cart"],
            {"tenis de corrida": 2, "bolsa preta": 1},
        )

    def test_checkout_generates_order_and_clears_cart(self):
        interpreter.reply("session-1", "adicionar 1 mochila ao carrinho")
        response = interpreter.reply("session-1", "fechar pedido no pix")

        self.assertIn("PIX copia-e-cola", response)
        self.assertEqual(store.get_cart("session-1")["cart"], {})
        self.assertRegex(response, r"PED-\d{8}-[0-9A-F]{6}")

    def test_known_order_status_is_returned(self):
        interpreter.reply("session-1", "adicionar 1 camiseta")
        checkout = interpreter.reply("session-1", "finalizar compra")
        order_id = re.search(r"PED-\d{8}-[0-9A-F]{6}", checkout).group(0)

        response = interpreter.reply("session-1", f"qual o status do pedido {order_id}?")

        self.assertIn(order_id, response)
        self.assertRegex(response, r"Processando|Enviado")

    def test_unknown_order_status(self):
        response = interpreter.reply("session-1", "status do pedido PED-20260727-ABC123")

        self.assertEqual(response, "Pedido nao encontrado.")


if __name__ == "__main__":
    unittest.main()
