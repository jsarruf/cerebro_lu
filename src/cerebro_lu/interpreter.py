"""Deterministic chat engine used for local development and tests."""

from __future__ import annotations

import re
import unicodedata

from . import tools
from .services import SalesService

NUMBER_WORDS = {
    "um": 1,
    "uma": 1,
    "dois": 2,
    "duas": 2,
    "tres": 3,
    "quatro": 4,
    "cinco": 5,
    "seis": 6,
    "sete": 7,
    "oito": 8,
    "nove": 9,
    "dez": 10,
}

ADD_VERBS = [
    "adicionar",
    "adicione",
    "adiciona",
    "colocar",
    "coloque",
    "incluir",
    "inclua",
    "comprar",
    "compre",
]


def reply(
    session_id: str,
    message: str,
    service: SalesService | None = None,
) -> str:
    """Interpret a user message and return the assistant text only."""

    normalized = _normalize(message)
    active_service = service or tools.sales_service

    if _is_checkout(normalized):
        response = _checkout_response(session_id, active_service)
    elif _is_clear_cart(normalized):
        response = _clear_response(session_id, active_service)
    elif _is_status_query(normalized):
        response = _status_response(normalized, active_service)
    elif _is_remove(normalized):
        response = _remove_response(session_id, normalized, active_service)
    elif _is_cart_query(normalized):
        response = _cart_response(session_id, active_service)
    elif _is_add(normalized):
        response = _add_response(session_id, normalized, active_service)
    else:
        response = (
            "Posso ajudar voce a adicionar produtos, remover itens, limpar o carrinho, "
            "fechar o pedido via PIX ou consultar o status de um pedido."
        )

    return response


def _add_response(
    session_id: str,
    normalized: str,
    service: SalesService,
) -> str:
    quantity, product = _extract_quantity_and_product(normalized)
    result = service.add_product(session_id, product, quantity)
    if not result["ok"]:
        return result["message"]

    item_word = "item" if result["total_items"] == 1 else "itens"
    return (
        f"Perfeito! Adicionei {result['quantity']} {result['product']} ao seu carrinho. "
        f"Seu carrinho agora tem {result['total_items']} {item_word}."
    )


def _remove_response(
    session_id: str,
    normalized: str,
    service: SalesService,
) -> str:
    product = _extract_after_verbs(normalized, ["remover", "retirar", "tirar"])
    result = service.remove_product(session_id, product)
    if not result["ok"]:
        return result["message"]
    if not result["cart"]:
        return f"Removi {result['product']} do carrinho. Seu carrinho ficou vazio."
    return f"Removi {result['product']} do carrinho. Ainda ha: {_format_cart(result['cart'])}."


def _clear_response(session_id: str, service: SalesService) -> str:
    result = service.clear_cart(session_id)
    if not result["ok"]:
        return result["message"]
    return "Pronto! Limpei todo o seu carrinho."


def _cart_response(session_id: str, service: SalesService) -> str:
    result = service.get_cart(session_id)
    if not result["ok"]:
        return result["message"]
    if not result["cart"]:
        return "Seu carrinho esta vazio no momento."
    return f"Seu carrinho tem {_format_cart(result['cart'])}."


def _checkout_response(session_id: str, service: SalesService) -> str:
    result = service.checkout_pix(session_id)
    if not result["ok"]:
        return result["message"]
    return (
        "Pedido fechado com sucesso! "
        f"ID do pedido: {result['order_id']}. "
        f"PIX copia-e-cola: {result['pix_code']}. "
        "Esvaziei seu carrinho para a proxima compra."
    )


def _status_response(normalized: str, service: SalesService) -> str:
    order_id = _extract_order_id(normalized)
    if not order_id:
        return "Me envie o ID do pedido para eu consultar o status."
    result = service.get_order_status(order_id)
    if not result["ok"]:
        return "Pedido nao encontrado."
    return f"O pedido {result['order_id']} esta com status: {result['status']}."


def _extract_quantity_and_product(normalized: str) -> tuple[int, str]:
    cleaned = _extract_after_verbs(normalized, ADD_VERBS)
    match = re.match(r"(?P<qty>\d+|um|uma|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez)\s+(?P<product>.+)", cleaned)
    if match:
        quantity = _parse_quantity(match.group("qty"))
        product = match.group("product")
    else:
        quantity = 1
        product = cleaned

    product = re.sub(r"\s+(ao|no|na|para|pro)\s+(meu|minha|o|a)?\s*carrinho.*$", "", product).strip()
    return quantity, product


def _extract_after_verbs(normalized: str, verbs: list[str]) -> str:
    pattern = "|".join(re.escape(verb) for verb in verbs)
    match = re.search(rf"(?:{pattern})\s+(?P<tail>.+)", normalized)
    tail = match.group("tail") if match else normalized
    tail = re.sub(r"^(o|a|os|as|um|uma)\s+", "", tail)
    tail = re.sub(r"\s+(do|da|de|no|na|ao|a partir do)\s+carrinho.*$", "", tail)
    return tail.strip(" .,!?:;")


def _extract_order_id(normalized: str) -> str | None:
    match = re.search(r"\bped-\d{8}-[0-9a-f]{6}\b", normalized)
    if match:
        return match.group(0).upper()
    loose = re.search(r"\bpedido\s+([a-z0-9-]{6,})", normalized)
    if loose:
        return loose.group(1).upper()
    return None


def _parse_quantity(value: str) -> int:
    if value.isdigit():
        return int(value)
    return NUMBER_WORDS.get(value, 1)


def _is_add(normalized: str) -> bool:
    return any(word in normalized for word in [*ADD_VERBS, "quero"])


def _is_remove(normalized: str) -> bool:
    return any(word in normalized for word in ["remover", "retirar", "tirar"])


def _is_clear_cart(normalized: str) -> bool:
    return ("limpar" in normalized or "esvaziar" in normalized) and "carrinho" in normalized


def _is_checkout(normalized: str) -> bool:
    return any(word in normalized for word in ["fechar", "finalizar", "checkout", "pagar", "pix"])


def _is_status_query(normalized: str) -> bool:
    return "status" in normalized or ("pedido" in normalized and "fechar" not in normalized)


def _is_cart_query(normalized: str) -> bool:
    return "carrinho" in normalized and any(word in normalized for word in ["ver", "mostrar", "consultar", "tem"])


def _format_cart(cart: dict[str, int]) -> str:
    return ", ".join(f"{quantity}x {product}" for product, quantity in cart.items())


def _normalize(message: str) -> str:
    without_accents = "".join(
        char
        for char in unicodedata.normalize("NFD", message.lower())
        if unicodedata.category(char) != "Mn"
    )
    return " ".join(without_accents.split())
