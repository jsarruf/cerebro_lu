"""Google ADK agent definition."""

from __future__ import annotations

from cerebro_lu.tools import (
    add_product,
    checkout_pix,
    clear_cart,
    get_cart,
    get_order_status,
    remove_product,
)
from cerebro_lu.config import get_settings

try:
    from google.adk.agents import Agent
except ModuleNotFoundError:  # Allows local unit tests without google-adk.
    Agent = None


INSTRUCTION = """
Voce e um Agente de Vendas Inteligente para ecommerce.

Responda sempre em portugues do Brasil, de forma objetiva e cordial.
Use exclusivamente as tools disponiveis para alterar carrinho, consultar
carrinho, fechar pedido via PIX e consultar status de pedido.

Regras:
- Use o session_id informado pela API quando chamar tools de carrinho.
- Considere o historico da sessao mantido pelo Runner para interpretar
  referencias a mensagens anteriores.
- Para adicionar produto, identifique product_name e quantity.
- Para remover produto, identifique product_name.
- No checkout, gere somente pedido PIX usando checkout_pix.
- Nunca invente produtos no carrinho, IDs, codigo PIX ou status.
- Depois de consultar uma tool, responda ao usuario apenas com o texto final.
- Nunca exponha eventos internos do ADK, logs, JSON de tool ou raciocinio.
"""


if Agent is None:
    root_agent = None
else:
    settings = get_settings()
    root_agent = Agent(
        model=settings.adk_model,
        name="cerebro_lu_sales_agent",
        description="Agente de vendas com carrinho, checkout PIX e status de pedidos.",
        instruction=INSTRUCTION,
        tools=[
            add_product,
            remove_product,
            clear_cart,
            get_cart,
            checkout_pix,
            get_order_status,
        ],
    )
