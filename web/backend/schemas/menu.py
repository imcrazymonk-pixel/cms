"""Menu schemas — mirror the CMS `menus` table."""
from typing import Optional

from pydantic import BaseModel, Field


class MenuResponse(BaseModel):
    id: int
    name: str
    url: str
    location: str = "main"


class MenuCreate(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    location: str = "main"


class MenuUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    location: Optional[str] = None
