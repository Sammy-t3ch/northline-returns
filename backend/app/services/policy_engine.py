"""Deterministic refund policy engine. Runs BEFORE any LLM call."""

from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from pathlib import Path
import json
import re

from app.models.schemas import Order, PolicyResult

ORDERS_PATH = Path(__file__).parent.parent / "data" / "orders.json"
MAX_AGE_DAYS = 30
HIGH_VALUE_THRESHOLD = 500.0

INJECTION_PATTERNS = [
    r"ignore\s+(previous|all|above)\s+instructions?",
    r"you\s+are\s+now\s+(allowed|able|free)",
    r"disregard\s+(the\s+)?policy",
    r"override\s+(the\s+)?(rules|policy)",
    r"pretend\s+(you\s+are|to\s+be)",
    r"system\s*prompt",
    r"jailbreak",
    r"as\s+an?\s+unrestricted",
    r"forget\s+(everything|all\s+rules)",
]


def load_orders() -> List[Order]:
    with open(ORDERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [Order(**o) for o in data]


def find_orders_by_email(email: str) -> List[Order]:
    email_lower = email.strip().lower()
    return [o for o in load_orders() if o.email.strip().lower() == email_lower]


def find_order(order_id: str, email: Optional[str] = None) -> Optional[Order]:
    orders = load_orders()
    for o in orders:
        if o.order_id.upper() == order_id.upper():
            if email and o.email.strip().lower() != email.strip().lower():
                return None
            return o
    return None


def detect_injection(message: str) -> bool:
    text = message.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


def days_since_order(order_date_str: str) -> int:
    try:
        order_dt = datetime.strptime(order_date_str, "%Y-%m-%d")
        today = datetime(2026, 9, 28)
        return (today - order_dt).days
    except ValueError:
        return 999


def evaluate_policy(
    email: str,
    message: str,
    order_id: Optional[str] = None,
) -> PolicyResult:
    reasons: List[str] = []
    flags: dict = {}

    if detect_injection(message):
        flags["injection_detected"] = True
        return PolicyResult(
            decision="Escalated",
            reasons=["Suspicious request language detected — requires human review."],
            matched_order=None,
            policy_flags=flags,
        )

    matched: Optional[Order] = None
    if order_id:
        matched = find_order(order_id, email)
        if not matched:
            candidate = find_order(order_id)
            if candidate:
                return PolicyResult(
                    decision="Denied",
                    reasons=[f"Order {order_id} does not belong to the email provided."],
                    matched_order=None,
                    policy_flags={"email_mismatch": True},
                )
            return PolicyResult(
                decision="Denied",
                reasons=[f"Order {order_id} was not found."],
                matched_order=None,
                policy_flags={"order_not_found": True},
            )
    else:
        candidates = find_orders_by_email(email)
        if not candidates:
            return PolicyResult(
                decision="Denied",
                reasons=["No orders found for this email address."],
                matched_order=None,
                policy_flags={"no_orders": True},
            )
        candidates.sort(key=lambda o: o.order_date, reverse=True)
        matched = candidates[0]
        if len(candidates) > 1:
            reasons.append(
                f"Multiple orders found; evaluating most recent ({matched.order_id})."
            )

    assert matched is not None
    flags["order_id"] = matched.order_id
    flags["order_total"] = matched.total

    age = days_since_order(matched.order_date)
    flags["days_since_order"] = age
    if age > MAX_AGE_DAYS:
        reasons.append(f"Order is {age} days old (limit is {MAX_AGE_DAYS} days).")
        return PolicyResult(
            decision="Denied",
            reasons=reasons,
            matched_order=matched,
            policy_flags=flags,
        )

    final_sale_items = [i for i in matched.items if i.final_sale]
    if final_sale_items and len(final_sale_items) == len(matched.items):
        names = ", ".join(i.name for i in final_sale_items)
        reasons.append(f"All items are final sale and not eligible for refund: {names}.")
        return PolicyResult(
            decision="Denied",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "final_sale": True},
        )
    if final_sale_items:
        names = ", ".join(i.name for i in final_sale_items)
        reasons.append(
            f"Note: some items are final sale ({names}) and cannot be refunded; "
            "remaining eligible items may still be considered."
        )
        flags["partial_final_sale"] = True

    if matched.total > HIGH_VALUE_THRESHOLD:
        reasons.append(
            f"Order total ${matched.total:.2f} exceeds ${HIGH_VALUE_THRESHOLD:.0f} "
            "auto-approval limit — human review required."
        )
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "high_value": True},
        )

    damage_keywords = [
        "damaged", "defective", "broken", "wrong item", "incorrect item",
        "not as described", "missing", "arrived broken", "faulty",
    ]
    msg_lower = message.lower()
    if any(k in msg_lower for k in damage_keywords):
        reasons.append(
            "Customer reported damage/defect/incorrect item — escalate for evidence review."
        )
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "damage_claim": True},
        )

    if matched.status in ("processing", "shipped"):
        reasons.append(
            f"Order status is '{matched.status}' — item may not have been received yet."
        )
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "not_delivered": True},
        )

    reasons.append(
        f"Order {matched.order_id} is within the {MAX_AGE_DAYS}-day window, "
        f"not fully final-sale, and under ${HIGH_VALUE_THRESHOLD:.0f}."
    )
    return PolicyResult(
        decision="Approved",
        reasons=reasons,
        matched_order=matched,
        policy_flags=flags,
    )
