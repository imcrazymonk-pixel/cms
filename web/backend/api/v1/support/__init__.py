"""Support API — Phase 1: health, config, conversations, customer cards, WS.

Mounted by main.py with prefix /api/support. Response format: {success, data}.
"""
from fastapi import APIRouter

from web.backend.api.v1.support.conversations import router as conversations_router
from web.backend.api.v1.support.health import router as health_router
from web.backend.api.v1.support.status import router as status_router
from web.backend.api.v1.support.ws import router as ws_router

router = APIRouter()
router.include_router(health_router, tags=["support"])
router.include_router(status_router, tags=["support"])
router.include_router(conversations_router, tags=["support"])
router.include_router(ws_router, tags=["support"])
