"""Media schemas — file-system backed (no DB table)."""
from pydantic import BaseModel


class MediaItemResponse(BaseModel):
    path: str
    url: str
    name: str
    size: int
    modified: int


class MediaDeleteRequest(BaseModel):
    path: str
