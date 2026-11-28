"""Support API — Phase 1: health, config, conversations, customer cards, WS.

Mounted by main.py with prefix /api/support. Response format: {success, data}.
"""
from fastapi import APIRouter

from web.backend.api.v1.support.assistant import router as assistant_router
from web.backend.api.v1.support.attachments import router as attachments_router
from web.backend.api.v1.support.analytics import router as analytics_router
from web.backend.api.v1.support.conversations import router as conversations_router
from web.backend.api.v1.support.feedback import router as feedback_router
from web.backend.api.v1.support.health import router as health_router
from web.backend.api.v1.support.imports import router as imports_router
from web.backend.api.v1.support.kb import router as kb_router
from web.backend.api.v1.support.notes import router as notes_router
from web.backend.api.v1.support.presence import router as presence_router
from web.backend.api.v1.support.sla import router as sla_router
from web.backend.api.v1.support.status import router as status_router
from web.backend.api.v1.support.templates import router as templates_router
from web.backend.api.v1.support.team import router as team_router
from web.backend.api.v1.support.suggestions import router as suggestions_router
from web.backend.api.v1.support.ws import router as ws_router

router = APIRouter()
router.include_router(health_router, tags=["support"])
router.include_router(status_router, tags=["support"])
router.include_router(conversations_router, tags=["support"])
router.include_router(templates_router, tags=["support"])
router.include_router(notes_router, tags=["support"])
router.include_router(presence_router, tags=["support"])
router.include_router(sla_router, tags=["support"])
router.include_router(suggestions_router, tags=["support"])
router.include_router(assistant_router, tags=["support"])
router.include_router(imports_router, tags=["support"])
router.include_router(kb_router, tags=["support"])
router.include_router(feedback_router, tags=["support"])
router.include_router(attachments_router, tags=["support"])
router.include_router(analytics_router, tags=["support"])
router.include_router(team_router, tags=["support"])
router.include_router(ws_router, tags=["support"])
