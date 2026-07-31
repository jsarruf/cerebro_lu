"""Business rules for carts, orders, and conversation history."""

from __future__ import annotations

import re
from collections.abc import Callable
from datetime import UTC, datetime
from random import choice
from secrets import token_hex

from .logging_config import get_logger
from .models import (
    AddProductResult,
    CartResult,
    ChatMessage,
    CheckoutResult,
    ErrorResult,
    MessageRole,
    Order,
    OrderStatus,
    OrderStatusResult,
    RemoveProductResult,
)
from .repository import SalesRepository

logger = get_logger("services")

ORDER_STATUSES: tuple[OrderStatus, ...] = ("Processando", "Enviado")
MAX_PRODUCT_NAME_LENGTH = 200
MAX_QUANTITY = 1_000
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
StatusSelector = Callable[[tuple[OrderStatus, ...]], OrderStatus]


class SalesService:
    """Centralize every business rule exposed by the sales tools."""

    def __init__(
        self,
        repository: SalesRepository,
        status_selector: StatusSelector = choice,
    ) -> None:
        self._repository = repository
        self._status_selector = status_selector

    def reset(self) -> None:
        """Clear state. Intended for isolated tests."""

        self._repository.reset()

    def add_product(
        self,
        session_id: str,
        product_name: str,
        quantity: int,
    ) -> AddProductResult:
        """Validate and add an item to a session cart."""

        if not _valid_session(session_id):
            return _error("Session ID invalido.")
        if quantity <= 0:
            return _error("A quantidade precisa ser maior que zero.")
        if quantity > MAX_QUANTITY:
            return _error(f"A quantidade maxima por operacao e {MAX_QUANTITY}.")

        product = _normalize_product(product_name)
        if not product:
            return _error("Nao consegui identificar o produto.")
        if len(product) > MAX_PRODUCT_NAME_LENGTH:
            return _error(
                f"O nome do produto deve ter ate {MAX_PRODUCT_NAME_LENGTH} caracteres."
            )

        cart = self._repository.add_cart_item(
            session_id.strip(),
            product,
            quantity,
        )
        return {
            "ok": True,
            "product": product,
            "quantity": quantity,
            "cart": cart,
            "total_items": sum(cart.values()),
        }

    def remove_product(
        self,
        session_id: str,
        product_name: str,
    ) -> RemoveProductResult:
        """Remove the best matching item from a session cart."""

        if not _valid_session(session_id):
            return {**_error("Session ID invalido."), "cart": {}}

        product = _normalize_product(product_name)
        cart = self._repository.get_cart(session_id.strip())
        matched = _find_product(cart, product)
        if matched is None:
            return {
                "ok": False,
                "message": f"Nao encontrei {product or 'esse item'} no carrinho.",
                "cart": cart,
            }

        self._repository.remove_cart_item(session_id.strip(), matched)
        return {
            "ok": True,
            "product": matched,
            "cart": self._repository.get_cart(session_id.strip()),
        }

    def clear_cart(self, session_id: str) -> CartResult:
        """Remove every item from a valid session cart."""

        if not _valid_session(session_id):
            return _error("Session ID invalido.")
        self._repository.clear_cart(session_id.strip())
        return {"ok": True, "cart": {}, "total_items": 0}

    def get_cart(self, session_id: str) -> CartResult:
        """Return a cart snapshot for a valid session."""

        if not _valid_session(session_id):
            return _error("Session ID invalido.")
        cart = self._repository.get_cart(session_id.strip())
        return {"ok": True, "cart": cart, "total_items": sum(cart.values())}

    def checkout_pix(self, session_id: str) -> CheckoutResult:
        """Create a PIX order and clear the cart atomically for the caller."""

        if not _valid_session(session_id):
            return _error("Session ID invalido.")

        normalized_session = session_id.strip()
        while True:
            cart = self._repository.get_cart(normalized_session)
            if not cart:
                return _error(
                    "Seu carrinho esta vazio. "
                    "Adicione um produto antes de fechar o pedido."
                )
            order_id = self._new_order_id()
            order = Order(
                order_id=order_id,
                session_id=normalized_session,
                items=cart,
                pix_code=self._new_pix_code(order_id),
                created_at=datetime.now(UTC),
            )
            if self._repository.save_order_and_clear_cart(order):
                break

        logger.info(
            "checkout_completed",
            extra={
                "session_id": normalized_session,
                "order_id": order.order_id,
            },
        )
        return {
            "ok": True,
            "order_id": order.order_id,
            "pix_code": order.pix_code,
            "items": dict(order.items),
        }

    def get_order_status(self, order_id: str) -> OrderStatusResult:
        """Return a simulated status for an existing order."""

        normalized = order_id.strip().upper()
        order = self._repository.get_order(normalized)
        if order is None:
            logger.warning(
                "order_not_found",
                extra={"order_id": normalized or "empty"},
            )
            return _error("Pedido nao encontrado.")

        status = self._status_selector(ORDER_STATUSES)
        logger.info(
            "order_status_checked",
            extra={"order_id": normalized},
        )
        return {"ok": True, "order_id": normalized, "status": status}

    def record_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
    ) -> None:
        """Persist one message for a valid conversation session."""

        if not _valid_session(session_id):
            raise ValueError("Session ID invalido.")
        self._repository.append_history(
            session_id.strip(),
            ChatMessage(
                role=role,
                content=content,
                created_at=datetime.now(UTC),
            ),
        )

    def get_history(self, session_id: str) -> tuple[ChatMessage, ...]:
        """Return the complete ordered history for a session."""

        if not _valid_session(session_id):
            return ()
        return self._repository.get_history(session_id.strip())

    @staticmethod
    def _new_order_id() -> str:
        today = datetime.now(UTC).strftime("%Y%m%d")
        return f"PED-{today}-{token_hex(3).upper()}"

    @staticmethod
    def _new_pix_code(order_id: str) -> str:
        return (
            "00020126580014BR.GOV.BCB.PIX0136"
            f"{token_hex(16)}"
            "5204000053039865802BR5920CEREBRO DA LU6009SAO PAULO"
            f"62070503***6304{order_id[-4:]}"
        )


def _valid_session(session_id: str) -> bool:
    return bool(session_id and SESSION_ID_PATTERN.fullmatch(session_id.strip()))


def _normalize_product(product_name: str) -> str:
    return " ".join(product_name.strip(" .,!?:;").split()).lower()


def _find_product(cart: dict[str, int], product: str) -> str | None:
    if product in cart:
        return product
    for item in cart:
        if product and (product in item or item in product):
            return item
    return None


def _error(message: str) -> ErrorResult:
    return {"ok": False, "message": message}
