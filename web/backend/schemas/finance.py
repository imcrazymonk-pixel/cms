"""Finance schemas — mirror web/backend/api/v1/finance.py (+ React api/finance.ts)."""
from typing import List, Optional

from pydantic import BaseModel, Field


class TransactionResponse(BaseModel):
    id: int
    date: str
    date_display: str
    month: str
    type: str  # 'income' | 'expense'
    participant: str = ""
    category: str = ""
    amount: float
    description: str = ""


class TransactionCreate(BaseModel):
    date: str
    type: str = Field(..., pattern="^(income|expense)$")
    category: str = ""
    participant: str = ""
    amount: float = 0
    description: str = ""


class TransactionUpdate(BaseModel):
    id: int
    date: Optional[str] = None
    type: Optional[str] = None
    category: Optional[str] = None
    participant: Optional[str] = None
    amount: Optional[float] = None
    description: Optional[str] = None


class ChartPoint(BaseModel):
    key: str
    label: str
    income: float = 0
    expense: float = 0
    balance: float = 0


class DeleteBulkRequest(BaseModel):
    ids: List[int] = Field(default_factory=list)
