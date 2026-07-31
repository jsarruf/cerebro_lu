"""Domain models and typed operation results."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal, TypedDict

MessageRole = Literal["user", "assistant"]
OrderStatus = Literal["Processando", "Enviado"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One message persisted in a conversation session."""

    role: MessageRole
    content: str
    created_at: datetime


@dataclass(slots=True)
class SessionState:
    """Mutable data owned by one conversational session."""

    cart: dict[str, int] = field(default_factory=dict)
    history: list[ChatMessage] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Order:
    """Fictitious order generated during checkout."""

    order_id: str
    session_id: str
    items: dict[str, int]
    pix_code: str
    created_at: datetime


class ErrorResult(TypedDict):
    """Standard service error returned to ADK tools."""

    ok: Literal[False]
    message: str


class AddProductSuccess(TypedDict):
    """Successful cart addition."""

    ok: Literal[True]
    product: str
    quantity: int
    cart: dict[str, int]
    total_items: int


class RemoveProductSuccess(TypedDict):
    """Successful cart removal."""

    ok: Literal[True]
    product: str
    cart: dict[str, int]


class RemoveProductError(ErrorResult):
    """Cart removal error including the unchanged cart."""

    cart: dict[str, int]


class CartSuccess(TypedDict):
    """Current cart snapshot."""

    ok: Literal[True]
    cart: dict[str, int]
    total_items: int


class CheckoutSuccess(TypedDict):
    """Successful checkout data."""

    ok: Literal[True]
    order_id: str
    pix_code: str
    items: dict[str, int]


class OrderStatusSuccess(TypedDict):
    """Status returned for a known order."""

    ok: Literal[True]
    order_id: str
    status: OrderStatus


AddProductResult = AddProductSuccess | ErrorResult
RemoveProductResult = RemoveProductSuccess | RemoveProductError
CartResult = CartSuccess | ErrorResult
CheckoutResult = CheckoutSuccess | ErrorResult
OrderStatusResult = OrderStatusSuccess | ErrorResult
