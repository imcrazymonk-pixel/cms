"""Theme schemas — mirror web/backend/core/theme_config.py + settings storage."""
from typing import Dict, Optional

from pydantic import BaseModel


class ThemeOption(BaseModel):
    label: str
    type: str = "text"
    default: str = ""
    value: str = ""
    hint: Optional[str] = None
    rows: Optional[int] = None
    options: Optional[Dict[str, str]] = None


class ThemeSettingsResponse(BaseModel):
    theme: str
    label: str
    options: Dict[str, ThemeOption]


# POST body: arbitrary option keys -> string values (saved as "<theme>_<key>").
ThemeSettingsUpdate = Dict[str, str]
