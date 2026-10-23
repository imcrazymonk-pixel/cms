"""Support integrations — external data behind the customer card (phase 1).

Phase 1: Bedolaga (user, subscriptions, tickets, transactions) with a 60s
cache in support_customer_profile.meta. Remnawave deep card — phase 5.
"""
from web.backend.core.support.integrations.bedolaga_customer import build_customer_card

__all__ = ["build_customer_card"]
