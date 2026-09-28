from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any


class OrderItem(BaseModel):
    sku: str
    name: str
    price: float
    final_sale: bool = False


class Order(BaseModel):
    order_id: str
    customer_id: str
    email: str
    customer_name: str
    order_date: str
    items: List[OrderItem]
    total: float
    status: str
    shipping_address: str


class RefundRequest(BaseModel):
    email: str = Field(..., min_length=3, description="Email on the order")
    order_id: Optional[str] = Field(None, description="Optional order ID")
    message: str = Field(..., min_length=1, description="Customer refund request message")


class PolicyResult(BaseModel):
    decision: Literal["Approved", "Denied", "Escalated"]
    reasons: List[str]
    matched_order: Optional[Order] = None
    policy_flags: Dict[str, Any] = Field(default_factory=dict)


class RefundResponse(BaseModel):
    request_id: str
    decision: Literal["Approved", "Denied", "Escalated"]
    customer_reply: str
    reasons: List[str]
    order_id: Optional[str] = None
    order_total: Optional[float] = None
    timestamp: str
    audit_notes: List[str] = Field(default_factory=list)


class AdminRequestLog(BaseModel):
    request_id: str
    email: str
    order_id: Optional[str] = None
    message: str
    decision: str
    reasons: List[str]
    customer_reply: str
    timestamp: str
    audit_notes: List[str] = Field(default_factory=list)
