import { useEffect, useState } from "react";
import "./PolicyView.css";

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function PolicyView() {
  // Read the live model name from the API so this page cannot drift from the
  // backend the way a hardcoded string does.
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let alive = true;
    fetch(`${API_BASE}/api/health`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (alive && data) setHealth(data);
      })
      .catch(() => {
        /* policy text is still useful if the API is down */
      });
    return () => {
      alive = false;
    };
  }, []);

  return (
    <article className="policy">
      <h2>Northline Care — Refund Policy</h2>
      <p className="lede">
        Deterministic rules run in the backend before any NVIDIA call. The model
        only drafts the customer-facing reply and cannot override a denial or
        escalation.
      </p>

      <section>
        <h3>1. Eligibility window</h3>
        <p>
          Refund requests must be submitted within <strong>30 days</strong> of
          the order date. Older orders are denied (except damage claims, which
          escalate).
        </p>
      </section>

      <section>
        <h3>2. Final sale</h3>
        <p>
          Items marked <code>final_sale: true</code> are not eligible. If the
          entire order is final sale → Denied. Partial final-sale orders note
          the restriction in audit reasons. A damage claim on a final-sale order
          is still denied, but the claim is recorded in the audit trail so a
          human can review it.
        </p>
      </section>

      <section>
        <h3>3. High-value review</h3>
        <p>
          Any order totaling more than <strong>$500</strong> is Escalated for
          human review. The AI never auto-approves above this threshold.
        </p>
      </section>

      <section>
        <h3>4. Damage / defect / incorrect item</h3>
        <p>
          Language such as damaged, defective, broken, faulty, torn, or "sent
          the wrong item" triggers <strong>Escalated</strong> so evidence can be
          reviewed. This check runs <em>before</em> the 30-day window, so a
          damaged item on an older order is reviewed rather than auto-denied.
          Only a fully final-sale order still denies outright.
        </p>
      </section>

      <section>
        <h3>5. Delivery confirmation — fails closed</h3>
        <p>
          Only an order explicitly marked <code>delivered</code> can be
          auto-approved. Orders still <code>processing</code> or{" "}
          <code>shipped</code> escalate, and so does <em>any</em> unrecognised
          status — a mistyped value never results in an automatic payout. An
          order with no line items is escalated as malformed data.
        </p>
      </section>

      <section>
        <h3>6. Prompt-injection safeguards</h3>
        <p>
          Messages that attempt to override policy (“ignore previous
          instructions”, “you are now allowed…”) are detected with pattern
          matching and Escalated, and the matched order is withheld from the
          response. Repeat requests for the same order are flagged in the audit
          trail for the reviewer. The policy engine decision is final.
        </p>
      </section>

      <section>
        <h3>7. Rule order</h3>
        <ol>
          <li>Injection / policy-bypass language → Escalated</li>
          <li>Resolve the order (email + order ID must match) → else Denied</li>
          <li>No line items on the order → Escalated</li>
          <li>Entire order final sale → Denied</li>
          <li>Damage / defect / incorrect item → Escalated</li>
          <li>Older than 30 days → Denied</li>
          <li>Order total over $500 → Escalated</li>
          <li>Not confirmed delivered → Escalated</li>
          <li>Otherwise → Approved</li>
        </ol>
      </section>

      <section>
        <h3>8. Outcomes</h3>
        <ul>
          <li>
            <strong>Approved</strong> — policy satisfied; refund can proceed
          </li>
          <li>
            <strong>Denied</strong> — clear violation (age, final sale, mismatch)
          </li>
          <li>
            <strong>Escalated</strong> — human required (value, damage,
            suspicion, not delivered)
          </li>
        </ul>
      </section>

      <section>
        <h3>Architecture note</h3>
        <p>
          Mock CRM: JSON order store (17 orders across 16 customers). Policy
          engine evaluates first. NVIDIA NIM generates the reply only, over an
          OpenAI-compatible endpoint — currently{" "}
          <code>{health ? health.model : "the configured NVIDIA_MODEL"}</code>.
          Audit log is kept in memory for the Desk view.
        </p>
      </section>
    </article>
  );
}
