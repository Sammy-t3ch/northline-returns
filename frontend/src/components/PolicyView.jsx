import "./PolicyView.css";

export default function PolicyView() {
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
          the restriction in audit reasons.
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
          Keywords such as damaged, defective, broken, wrong item trigger
          Escalated so evidence can be reviewed.
        </p>
      </section>

      <section>
        <h3>5. Prompt-injection safeguards</h3>
        <p>
          Messages that attempt to override policy (“ignore previous
          instructions”, “you are now allowed…”) are detected with pattern
          matching and Escalated. The policy engine decision is final.
        </p>
      </section>

      <section>
        <h3>6. Outcomes</h3>
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
          Mock CRM: JSON order store (~15 customers). Policy engine evaluates
          first. NVIDIA NIM (Llama 3.1 70B via OpenAI-compatible API) generates
          the reply only. Audit log is kept in memory for the Desk view.
        </p>
      </section>
    </article>
  );
}
