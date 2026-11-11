"""Deterministic refund policy engine. Runs BEFORE any LLM call."""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
from pathlib import Path
import json
import re

from app.models.schemas import Order, PolicyResult

ORDERS_PATH = Path(__file__).parent.parent / "data" / "orders.json"
MAX_AGE_DAYS = 30
HIGH_VALUE_THRESHOLD = 500.0

# Only these (lower-cased, trimmed) statuses count as a confirmed delivery.
# Anything unrecognised fails closed to Escalated rather than auto-approving.
DELIVERED_STATUSES = {"delivered"}

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

# Damage / defect / incorrect-item language. Word-boundary anchored and
# inflection-aware so "damage", "damaged" and "damaging" all match, while
# substrings inside unrelated words do not. A hit means "route to a human for
# evidence review", never "auto-approve".
DAMAGE_PATTERNS = [
    r"\bdamag(?:e|ed|es|ing)\b",
    r"\bdefect(?:s|ive|ively)?\b",
    r"\bbroken\b",
    r"\bfault(?:y|s)?\b",
    r"\bmalfunction(?:s|ed|ing)?\b",
    r"\b(?:wrong|incorrect)\s+(?:item|items|product|order|colour|color|model)\b",
    r"\bsent\s+(?:me\s+)?(?:the\s+)?wrong\b",
    r"\bnot\s+as\s+described\b",
    r"\bmissing\b",
    r"\b(?:torn|ripped|tear|hole|crack(?:ed)?|dent(?:ed)?|bent|shatter(?:ed)?)\b",
    r"\bleak(?:s|ed|ing)?\b",
    r"\b(?:do(?:es)?n'?t|not|never|stopped|won'?t)\s+work(?:s|ing)?\b",
    r"\bdead\s+on\s+arrival\b",
]

_COMPILED_INJECTION = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]
_COMPILED_DAMAGE = [re.compile(p, re.IGNORECASE) for p in DAMAGE_PATTERNS]


def _hydrate_order(raw: dict) -> Order:
    """Resolve relative dates so demo scenarios never expire."""
    payload = dict(raw)
    days = payload.pop("days_ago", None)
    if days is not None:
        payload["order_date"] = (
            datetime.now(timezone.utc).date() - timedelta(days=int(days))
        ).isoformat()
    return Order(**payload)


def load_orders() -> List[Order]:
    with open(ORDERS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [_hydrate_order(o) for o in data]


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
    for pattern in _COMPILED_INJECTION:
        if pattern.search(text):
            return True
    return False


def detect_damage(message: str) -> Optional[str]:
    """Return the matched damage/defect phrase, or None.

    Policy §3: damaged, defective or incorrect items shipped by Northline are
    reviewed on evidence even outside the 30-day window, so this check has to
    run before the age gate rather than after it.
    """
    for pattern in _COMPILED_DAMAGE:
        match = pattern.search(message)
        if match:
            return match.group(0).strip().lower()
    return None


def days_since_order(order_date_str: str) -> int:
    try:
        order_dt = datetime.strptime(order_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        today = datetime.now(timezone.utc)
        return (today - order_dt).days
    except ValueError:
        return 999


def evaluate_policy(
    email: str,
    message: str,
    order_id: Optional[str] = None,
    prior_attempts: int = 0,
) -> PolicyResult:
    reasons: List[str] = []
    flags: dict = {}

    # 0. Repeat-request signal (policy §5). Passed in by the caller so the engine
    #    itself stays pure and unit-testable.
    if prior_attempts > 0:
        flags["repeat_attempt"] = True
        flags["prior_attempts"] = prior_attempts
        reasons.append(
            f"Repeat request — {prior_attempts} earlier attempt(s) already logged "
            "for this customer; flagged for reviewer attention."
        )

    # 1. Prompt-injection / policy-bypass attempt
    if detect_injection(message):
        flags["injection_detected"] = True
        return PolicyResult(
            decision="Escalated",
            reasons=["Suspicious request language detected — requires human review."],
            matched_order=None,
            policy_flags=flags,
        )

    # 2. Resolve order
    matched: Optional[Order] = None
    if order_id:
        wanted = order_id.strip().upper()
        candidate = next(
            (o for o in load_orders() if o.order_id.strip().upper() == wanted), None
        )
        if candidate is None:
            return PolicyResult(
                decision="Denied",
                reasons=[f"Order {order_id} was not found."],
                matched_order=None,
                policy_flags={**flags, "order_not_found": True},
            )
        if candidate.email.strip().lower() != email.strip().lower():
            return PolicyResult(
                decision="Denied",
                reasons=[
                    f"Order {order_id} does not belong to the email provided."
                ],
                matched_order=None,
                policy_flags={**flags, "email_mismatch": True},
            )
        matched = candidate
    else:
        candidates = find_orders_by_email(email)
        if not candidates:
            return PolicyResult(
                decision="Denied",
                reasons=["No orders found for this email address."],
                matched_order=None,
                policy_flags={**flags, "no_orders": True},
            )
        candidates.sort(key=lambda o: o.order_date, reverse=True)
        matched = candidates[0]
        if len(candidates) > 1:
            reasons.append(
                f"Multiple orders found; evaluating most recent ({matched.order_id})."
            )

    if matched is None:  # pragma: no cover - defensive, all branches above return
        return PolicyResult(
            decision="Escalated",
            reasons=["Could not resolve the order — human review required."],
            matched_order=None,
            policy_flags={"unresolved_order": True},
        )

    flags["order_id"] = matched.order_id
    flags["order_total"] = matched.total
    flags["order_status"] = matched.status
    # Computed once, up front, so every downstream branch carries the order age
    # into the audit log — not just the branches that happen to gate on it.
    flags["days_since_order"] = days_since_order(matched.order_date)

    # 3. An order with no line items is malformed data — never auto-approve it.
    if not matched.items:
        reasons.append("Order has no line items on record — human review required.")
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "no_line_items": True},
        )

    # 4. Damage / defect / incorrect item language is detected up front so the
    #    evidence-review rule can outrank the 30-day window (policy §3).
    damage_term = detect_damage(message)
    if damage_term:
        flags["damage_claim"] = True
        flags["damage_term"] = damage_term

    # 5. Final-sale items
    final_sale_items = [i for i in matched.items if i.final_sale]
    if final_sale_items and len(final_sale_items) == len(matched.items):
        names = ", ".join(i.name for i in final_sale_items)
        reasons.append(f"All items are final sale and not eligible for refund: {names}.")
        if damage_term:
            reasons.append(
                f"Customer also reported damage/defect (\"{damage_term}\"); final sale "
                "still applies, but the claim is flagged for manual review."
            )
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

    # 6. Damage / defect / incorrect item → escalate for evidence review.
    #    Runs before the age gate: policy §3 allows evidence-based review even
    #    outside the 30-day window.
    if damage_term:
        reasons.append(
            "Customer reported damage/defect/incorrect item — escalate for evidence review."
        )
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags=flags,
        )

    # 7. Age check
    age = flags["days_since_order"]
    if age > MAX_AGE_DAYS:
        reasons.append(
            f"Order is {age} days old (limit is {MAX_AGE_DAYS} days)."
        )
        return PolicyResult(
            decision="Denied",
            reasons=reasons,
            matched_order=matched,
            policy_flags=flags,
        )

    # 8. High-value threshold
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

    # 9. Delivery confirmation. Fails CLOSED: only an explicit delivered state
    #    may auto-approve. Anything else — shipped, processing, cancelled, or an
    #    unrecognised/typo'd status — goes to a human instead of paying out.
    status = (matched.status or "").strip().lower()
    if status not in DELIVERED_STATUSES:
        if status in ("processing", "shipped"):
            reasons.append(
                f"Order status is '{matched.status}' — item may not have been received yet."
            )
        else:
            reasons.append(
                f"Order status '{matched.status}' is not a confirmed delivery — "
                "human review required."
            )
        return PolicyResult(
            decision="Escalated",
            reasons=reasons,
            matched_order=matched,
            policy_flags={**flags, "not_delivered": True},
        )

    # Default path: eligible under deterministic rules
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
