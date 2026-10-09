"""Setting schemas — mirror the whitelisted keys in web/backend/api/v1/settings.py."""
from typing import Optional

from pydantic import BaseModel


class SettingsResponse(BaseModel):
    site_name: Optional[str] = None
    site_description: Optional[str] = None
    meta_keywords: Optional[str] = None
    meta_description: Optional[str] = None
    active_theme: Optional[str] = None
    posts_per_page: Optional[str] = None
    comments_auto_approve: Optional[str] = None
    maintenance_mode: Optional[str] = None
    docker_config: Optional[str] = None
    loki_config: Optional[str] = None


class SettingsUpdate(SettingsResponse):
    """Same whitelist on write; unknown keys are ignored by the router."""
