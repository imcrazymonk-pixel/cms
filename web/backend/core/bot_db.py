"""Read-only connection to Bot PostgreSQL (tariffs catalog).

Uses a separate async engine with minimal pool size.
Only SELECT queries — no writes possible (PostgreSQL user is read-only).
"""
import json
import logging
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from web.backend.core.config import get_cms_settings

logger = logging.getLogger(__name__)

_engine: Optional[AsyncEngine] = None


def _get_engine() -> Optional[AsyncEngine]:
    """Lazy-init read-only engine (1 connection, no pool)."""
    global _engine
    if _engine is not None:
        return _engine
    settings = get_cms_settings()
    url = settings.bot_database_url
    if not url:
        return None
    _engine = create_async_engine(
        url,
        pool_size=1,
        max_overflow=0,
        pool_recycle=300,
        pool_pre_ping=True,
    )
    return _engine


async def get_tariffs() -> list[dict]:
    """Get all tariffs from bot database."""
    engine = _get_engine()
    if not engine:
        logger.warning("Bot database not configured — set BOT_DB_HOST in .env")
        return []

    try:
        async with engine.connect() as conn:
            rows = await conn.execute(
                text("""
                    SELECT
                        id, name, description, is_active, display_order,
                        traffic_limit_gb, device_limit, device_price_kopeks, max_device_limit,
                        period_prices, tier_level,
                        is_trial_available, trial_duration_days,
                        is_daily, daily_price_kopeks,
                        custom_days_enabled, price_per_day_kopeks, min_days, max_days,
                        custom_traffic_enabled, traffic_price_per_gb_kopeks, min_traffic_gb, max_traffic_gb,
                        allow_traffic_topup, traffic_topup_enabled,
                        show_in_gift, is_highlighted, highlight_period_days,
                        traffic_reset_mode, external_squad_uuid, panel_tag,
                        lava_product_id, allowed_squads, server_traffic_limits,
                        created_at, updated_at
                    FROM tariffs
                    ORDER BY display_order, id
                """)
            )
            tariffs = []
            for row in rows:
                d = dict(row._mapping)
                # Parse JSON fields
                for json_field in ('period_prices', 'allowed_squads', 'server_traffic_limits', 'traffic_topup_packages'):
                    val = d.get(json_field)
                    if isinstance(val, str):
                        d[json_field] = json.loads(val)
                # Format period_prices for frontend
                if d.get('period_prices') and isinstance(d['period_prices'], dict):
                    d['period_prices_list'] = [
                        {'days': int(k), 'price_kopeks': int(v), 'price_rubles': round(int(v) / 100, 2)}
                        for k, v in sorted(d['period_prices'].items(), key=lambda x: int(x[0]))
                    ]
                else:
                    d['period_prices_list'] = []
                # Convert timestamps to strings
                for ts_field in ('created_at', 'updated_at'):
                    val = d.get(ts_field)
                    if val and hasattr(val, 'isoformat'):
                        d[ts_field] = val.isoformat()
                tariffs.append(d)
            return tariffs
    except Exception as e:
        logger.error("Failed to read tariffs from bot DB: %s", e, exc_info=True)
        return []


async def close_engine():
    """Dispose engine on shutdown."""
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None