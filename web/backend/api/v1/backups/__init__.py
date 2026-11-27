"""Backup module API (mounted at ``/api/backups``).

Vertical slice, same layout as ``api/v1/support`` and ``api/v1/bedolaga``.
"""
from fastapi import APIRouter

from . import alerts, artifacts, components, hosts, overview, policies, restore, runs, settings, storages

router = APIRouter()

router.include_router(overview.router, tags=["backups"])
router.include_router(hosts.router, prefix="/hosts", tags=["backups"])
router.include_router(components.router, prefix="/components", tags=["backups"])
router.include_router(storages.router, prefix="/storages", tags=["backups"])
router.include_router(policies.router, tags=["backups"])
router.include_router(runs.router, tags=["backups"])
router.include_router(artifacts.router, tags=["backups"])
router.include_router(restore.router, tags=["backups"])
router.include_router(alerts.router, prefix="/notifications", tags=["backups"])
router.include_router(settings.router, tags=["backups"])
