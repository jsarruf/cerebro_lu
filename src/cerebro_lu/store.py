"""Backward-compatible facade for the former store module.

New code should depend on ``SalesRepository`` and ``SalesService`` directly.
"""

from typing import cast

from .models import CheckoutResult, MessageRole
from .repository import InMemorySalesRepository
from .services import SalesService


class InMemoryStore(SalesService):
    """Preserve the original store methods while using the new layers."""

    def __init__(self) -> None:
        super().__init__(InMemorySalesRepository())

    def add_history(self, session_id: str, role: str, content: str) -> None:
        """Compatibility alias for the original history method."""

        if role not in {"user", "assistant"}:
            raise ValueError("Role de historico invalida.")
        self.record_message(session_id, cast(MessageRole, role), content)

    def checkout(self, session_id: str) -> CheckoutResult:
        """Compatibility alias for the original checkout method."""

        return self.checkout_pix(session_id)


__all__ = ["InMemorySalesRepository", "InMemoryStore"]
