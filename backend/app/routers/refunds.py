from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
import uuid

from app.models.schemas import (
    RefundRequest,
    RefundResponse,
    AdminRequestLog,
    Order,
)
from app.services.policy_engine import evaluate_policy, load_orders, find_orders_by_email
from app.services.nvidia_ai import generate_customer_reply

router = APIRouter(prefix="/api", tags=["refunds"])

# In-memory audit log (resets on restart — fine for assessment demo)
_AUDIT_LOG: List[AdminRequestLog] = []


@router.post("/refund", response_model=RefundResponse)
async def process_refund(body: RefundRequest):
    """Main entry: customer refund request → policy → AI reply → audit log."""
    if not body.email or not body.message.strip():
        raise HTTPException(status_code=400, detail="email and message are required")

    policy = evaluate_policy(
        email=body.email.strip(),
        message=body.message.strip(),
        order_id=body.order_id.strip() if body.order_id else None,
    )

    customer_reply = generate_customer_reply(
        customer_message=body.message.strip(),
        policy=policy,
        email=body.email.strip(),
    )

    request_id = f"REQ-{uuid.uuid4().hex[:8].upper()}"
    ts = datetime.now(timezone.utc).isoformat()

    audit_notes = [
        f"Policy decision: {policy.decision}",
        *[f"Reason: {r}" for r in policy.reasons],
    ]
    if policy.policy_flags:
        audit_notes.append(f"Flags: {policy.policy_flags}")

    response = RefundResponse(
        request_id=request_id,
        decision=policy.decision,
        customer_reply=customer_reply,
        reasons=policy.reasons,
        order_id=policy.matched_order.order_id if policy.matched_order else None,
        order_total=policy.matched_order.total if policy.matched_order else None,
        timestamp=ts,
        audit_notes=audit_notes,
    )

    _AUDIT_LOG.insert(
        0,
        AdminRequestLog(
            request_id=request_id,
            email=body.email.strip(),
            order_id=response.order_id,
            message=body.message.strip(),
            decision=policy.decision,
            reasons=policy.reasons,
            customer_reply=customer_reply,
            timestamp=ts,
            audit_notes=audit_notes,
        ),
    )
    # Keep last 100
    if len(_AUDIT_LOG) > 100:
        _AUDIT_LOG.pop()

    return response


@router.get("/admin/requests", response_model=List[AdminRequestLog])
async def list_requests(limit: int = 50):
    """Admin dashboard feed of recent refund decisions."""
    return _AUDIT_LOG[: max(1, min(limit, 100))]


@router.get("/orders", response_model=List[Order])
async def list_orders(email: str | None = None):
    """Optional helper: list mock orders (filter by email)."""
    if email:
        return find_orders_by_email(email)
    return load_orders()


@router.get("/health")
async def health():
    return {"status": "ok", "service": "northline-returns"}
