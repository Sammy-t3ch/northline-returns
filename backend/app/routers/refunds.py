from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
import os
import uuid

from app.models.schemas import (
    RefundRequest,
    RefundResponse,
    AdminRequestLog,
    Order,
)
from app.services.policy_engine import evaluate_policy, load_orders, find_orders_by_email
from app.services.nvidia_ai import (
    DEFAULT_MODEL,
    generate_customer_reply,
    nvidia_configured,
)

router = APIRouter(prefix="/api", tags=["refunds"])

# In-memory audit log (resets on restart — fine for assessment demo)
_AUDIT_LOG: List[AdminRequestLog] = []


def _count_prior_attempts(email: str, order_id: str | None) -> int:
    """How many requests this customer has already made for the same order.

    Policy §5 flags repeat attempts for reviewer attention. Scoped to the order
    when one is known, otherwise to the customer.
    """
    email_l = email.strip().lower()
    oid = (order_id or "").strip().upper()
    return sum(
        1
        for row in _AUDIT_LOG
        if row.email.strip().lower() == email_l
        and (not oid or (row.order_id or "").strip().upper() == oid)
    )


@router.post("/refund", response_model=RefundResponse)
async def process_refund(body: RefundRequest):
    """Main entry: customer refund request → policy → AI reply → audit log."""
    # Strip before validating: pydantic's min_length is satisfied by whitespace,
    # so "   " would otherwise reach the policy engine as an empty email.
    email = body.email.strip()
    message = body.message.strip()
    order_id = body.order_id.strip() if body.order_id else None

    if not email or not message:
        raise HTTPException(status_code=400, detail="email and message are required")
    prior_attempts = _count_prior_attempts(email, order_id)

    policy = evaluate_policy(
        email=email,
        message=message,
        order_id=order_id,
        prior_attempts=prior_attempts,
    )

    customer_reply = generate_customer_reply(
        customer_message=message,
        policy=policy,
        email=email,
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

    # When the engine deliberately withholds the order (injection, mismatch) the
    # audit trail still records what the customer asked about.
    logged_order_id = response.order_id or order_id

    _AUDIT_LOG.insert(
        0,
        AdminRequestLog(
            request_id=request_id,
            email=email,
            order_id=logged_order_id,
            message=message,
            decision=policy.decision,
            reasons=policy.reasons,
            customer_reply=customer_reply,
            timestamp=ts,
            audit_notes=audit_notes,
        ),
    )
    if len(_AUDIT_LOG) > 100:
        _AUDIT_LOG.pop()

    return response


@router.get("/admin/requests", response_model=List[AdminRequestLog])
async def list_requests(limit: int = 50):
    """Admin dashboard feed of recent refund decisions."""
    # Clamp to [0, 100]. Previously max(1, ...) meant limit=0 returned one row.
    return _AUDIT_LOG[: max(0, min(limit, 100))]


@router.get("/orders", response_model=List[Order])
async def list_orders(email: str | None = None):
    """Optional helper: list mock orders (filter by email)."""
    if email:
        return find_orders_by_email(email)
    return load_orders()


@router.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "northline-returns",
        "nvidia_configured": nvidia_configured(),
        "model": os.getenv("NVIDIA_MODEL", DEFAULT_MODEL),
    }
