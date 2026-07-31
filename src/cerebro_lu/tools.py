"""Function tools shared by the local service and the ADK agent."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import TypeVar

from .logging_config import get_logger
from .models import (
    AddProductResult,
    CartResult,
    CheckoutResult,
    OrderStatusResult,
    RemoveProductResult,
)
from .repository import InMemorySalesRepository
from .services import SalesService

logger = get_logger("tools")
ToolResult = TypeVar("ToolResult")

repository = InMemorySalesRepository()
sales_service = SalesService(repository)

# Compatibility for existing integrations and tests that imported tools.store.
store = sales_service


def add_product(
    session_id: str,
    product_name: str,
    quantity: int,
) -> AddProductResult:
    """Add a product to the cart associated with a session.

    Args:
        session_id: Stable identifier received in the API payload.
        product_name: Product description informed by the user.
        quantity: Positive number of units to add.

    Returns:
        A serializable result containing ``ok`` and either the updated cart
        data or a user-safe validation message.
    """

    return _execute_tool(
        "add_product",
        session_id,
        lambda: sales_service.add_product(session_id, product_name, quantity),
    )


def remove_product(
    session_id: str,
    product_name: str,
) -> RemoveProductResult:
    """Remove a matching product from the session cart.

    Args:
        session_id: Stable identifier received in the API payload.
        product_name: Product description to remove.

    Returns:
        A serializable result with the updated cart or a not-found message.
    """

    return _execute_tool(
        "remove_product",
        session_id,
        lambda: sales_service.remove_product(session_id, product_name),
    )


def clear_cart(session_id: str) -> CartResult:
    """Remove all products from the session cart.

    Args:
        session_id: Stable identifier received in the API payload.

    Returns:
        A serializable empty-cart snapshot or a validation message.
    """

    return _execute_tool(
        "clear_cart",
        session_id,
        lambda: sales_service.clear_cart(session_id),
    )


def get_cart(session_id: str) -> CartResult:
    """Return a snapshot of the cart associated with a session.

    Args:
        session_id: Stable identifier received in the API payload.

    Returns:
        A serializable cart snapshot and total item count.
    """

    return _execute_tool(
        "get_cart",
        session_id,
        lambda: sales_service.get_cart(session_id),
    )


def checkout_pix(session_id: str) -> CheckoutResult:
    """Create an order with a fictitious PIX code and clear the cart.

    Args:
        session_id: Stable identifier received in the API payload.

    Returns:
        A serializable order and PIX result, or an empty-cart message.
    """

    return _execute_tool(
        "checkout_pix",
        session_id,
        lambda: sales_service.checkout_pix(session_id),
    )


def get_order_status(order_id: str) -> OrderStatusResult:
    """Return a simulated status for an existing order.

    Args:
        order_id: Identifier returned by ``checkout_pix``.

    Returns:
        A serializable status result or a not-found message.
    """

    return _execute_tool(
        "get_order_status",
        None,
        lambda: sales_service.get_order_status(order_id),
    )


def _execute_tool(
    tool_name: str,
    session_id: str | None,
    operation: Callable[[], ToolResult],
) -> ToolResult:
    started_at = perf_counter()
    try:
        result = operation()
    except Exception as exc:
        logger.exception(
            "tool_failed",
            extra={
                "session_id": session_id,
                "tool": tool_name,
                "duration_ms": round((perf_counter() - started_at) * 1000, 2),
                "error_type": type(exc).__name__,
            },
        )
        raise

    logger.info(
        "tool_completed",
        extra={
            "session_id": session_id,
            "tool": tool_name,
            "duration_ms": round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return result
