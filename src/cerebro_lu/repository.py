"""Persistence contracts and the in-memory implementation."""

from __future__ import annotations

from dataclasses import replace
from threading import RLock
from typing import Protocol

from .models import ChatMessage, Order, SessionState


class SalesRepository(Protocol):
    """Data operations required by the sales domain."""

    def reset(self) -> None:
        """Remove every session and order."""

    def add_cart_item(
        self,
        session_id: str,
        product_name: str,
        quantity: int,
    ) -> dict[str, int]:
        """Increment an item and return an isolated cart snapshot."""

    def remove_cart_item(self, session_id: str, product_name: str) -> bool:
        """Remove an exact item, returning whether it existed."""

    def clear_cart(self, session_id: str) -> None:
        """Remove every item from a session cart."""

    def get_cart(self, session_id: str) -> dict[str, int]:
        """Return an isolated cart snapshot."""

    def append_history(self, session_id: str, message: ChatMessage) -> None:
        """Persist one conversation message."""

    def get_history(self, session_id: str) -> tuple[ChatMessage, ...]:
        """Return an immutable conversation snapshot."""

    def save_order_and_clear_cart(self, order: Order) -> bool:
        """Atomically persist an order and clear its unchanged source cart."""

    def get_order(self, order_id: str) -> Order | None:
        """Return an isolated order snapshot when it exists."""


class InMemorySalesRepository:
    """Thread-safe in-memory implementation of :class:`SalesRepository`."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionState] = {}
        self._orders: dict[str, Order] = {}
        self._lock = RLock()

    def reset(self) -> None:
        """Remove every session and order."""

        with self._lock:
            self._sessions.clear()
            self._orders.clear()

    def add_cart_item(
        self,
        session_id: str,
        product_name: str,
        quantity: int,
    ) -> dict[str, int]:
        """Increment an item and return an isolated cart snapshot."""

        with self._lock:
            cart = self._session(session_id).cart
            cart[product_name] = cart.get(product_name, 0) + quantity
            return dict(cart)

    def remove_cart_item(self, session_id: str, product_name: str) -> bool:
        """Remove an exact item, returning whether it existed."""

        with self._lock:
            cart = self._session(session_id).cart
            if product_name not in cart:
                return False
            cart.pop(product_name)
            return True

    def clear_cart(self, session_id: str) -> None:
        """Remove every item from a session cart."""

        with self._lock:
            self._session(session_id).cart.clear()

    def get_cart(self, session_id: str) -> dict[str, int]:
        """Return an isolated cart snapshot."""

        with self._lock:
            return dict(self._session(session_id).cart)

    def append_history(self, session_id: str, message: ChatMessage) -> None:
        """Persist one conversation message."""

        with self._lock:
            self._session(session_id).history.append(message)

    def get_history(self, session_id: str) -> tuple[ChatMessage, ...]:
        """Return an immutable conversation snapshot."""

        with self._lock:
            return tuple(self._session(session_id).history)

    def save_order_and_clear_cart(self, order: Order) -> bool:
        """Atomically persist an order and clear its unchanged source cart."""

        with self._lock:
            if order.order_id in self._orders:
                return False
            cart = self._session(order.session_id).cart
            if cart != order.items:
                return False
            self._orders[order.order_id] = replace(order, items=dict(order.items))
            cart.clear()
            return True

    def get_order(self, order_id: str) -> Order | None:
        """Return an isolated order snapshot when it exists."""

        with self._lock:
            order = self._orders.get(order_id)
            if order is None:
                return None
            return replace(order, items=dict(order.items))

    def _session(self, session_id: str) -> SessionState:
        return self._sessions.setdefault(session_id, SessionState())
