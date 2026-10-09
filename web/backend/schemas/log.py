"""Log schemas — mirror the CMS `app_logs` table."""
from typing import Optional

from pydantic import BaseModel


class LogResponse(BaseModel):
    id: int
    level: str
    category: Optional[str] = None
    channel: Optional[str] = None
    source: Optional[str] = None
    message: str
    context: Optional[str] = None
    created_at: Optional[str] = None


class LogClearRequest(BaseModel):
    category: Optional[str] = None
    channel: Optional[str] = None
