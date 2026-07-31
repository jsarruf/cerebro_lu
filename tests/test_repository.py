import unittest
from datetime import UTC, datetime

from cerebro_lu.models import ChatMessage, Order
from cerebro_lu.repository import InMemorySalesRepository


class InMemorySalesRepositoryTest(unittest.TestCase):
    def setUp(self):
        self.repository = InMemorySalesRepository()

    def test_cart_snapshots_do_not_expose_internal_state(self):
        snapshot = self.repository.add_cart_item("session-1", "tenis", 2)
        snapshot["tenis"] = 99

        self.assertEqual(self.repository.get_cart("session-1"), {"tenis": 2})

    def test_history_is_ordered_and_isolated_by_session(self):
        first = ChatMessage("user", "ola", datetime.now(UTC))
        second = ChatMessage("assistant", "oi", datetime.now(UTC))

        self.repository.append_history("session-1", first)
        self.repository.append_history("session-1", second)

        self.assertEqual(self.repository.get_history("session-1"), (first, second))
        self.assertEqual(self.repository.get_history("session-2"), ())

    def test_order_and_cart_update_are_atomic(self):
        self.repository.add_cart_item("session-1", "mochila", 1)
        order = Order(
            order_id="PED-20260727-ABC123",
            session_id="session-1",
            items={"mochila": 1},
            pix_code="pix",
            created_at=datetime.now(UTC),
        )

        saved = self.repository.save_order_and_clear_cart(order)

        self.assertTrue(saved)
        self.assertEqual(self.repository.get_cart("session-1"), {})
        self.assertEqual(self.repository.get_order(order.order_id), order)

    def test_order_is_rejected_if_cart_changed(self):
        self.repository.add_cart_item("session-1", "mochila", 1)
        order = Order(
            order_id="PED-20260727-ABC123",
            session_id="session-1",
            items={"mochila": 1},
            pix_code="pix",
            created_at=datetime.now(UTC),
        )
        self.repository.add_cart_item("session-1", "camiseta", 1)

        saved = self.repository.save_order_and_clear_cart(order)

        self.assertFalse(saved)
        self.assertEqual(
            self.repository.get_cart("session-1"),
            {"mochila": 1, "camiseta": 1},
        )


if __name__ == "__main__":
    unittest.main()
