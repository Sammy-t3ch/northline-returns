import { useEffect, useState } from "react";
import "./AdminDesk.css";

const API_BASE = import.meta.env.VITE_API_URL || "";

export default function AdminDesk() {
  const [rows, setRows] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/admin/requests?limit=50`);
      if (!res.ok) throw new Error("Failed to load requests");
      const data = await res.json();
      setRows(data);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="desk">
      <div className="desk-header">
        <div>
          <h2>Support desk</h2>
          <p>Recent refund decisions and audit notes</p>
        </div>
        <button type="button" className="refresh" onClick={load}>
          Refresh
        </button>
      </div>

      {loading && rows.length === 0 && <p className="muted">Loading…</p>}
      {error && <p className="error">{error}</p>}
      {!loading && rows.length === 0 && !error && (
        <p className="muted">
          No requests yet. Submit one from the Support tab.
        </p>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Time</th>
              <th>ID</th>
              <th>Email</th>
              <th>Order</th>
              <th>Decision</th>
              <th>Message</th>
              <th>Reasons</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.request_id}>
                <td className="mono">
                  {new Date(r.timestamp).toLocaleString()}
                </td>
                <td className="mono">{r.request_id}</td>
                <td>{r.email}</td>
                <td className="mono">{r.order_id || "—"}</td>
                <td>
                  <span
                    className={`decision decision-${r.decision.toLowerCase()}`}
                  >
                    {r.decision}
                  </span>
                </td>
                <td className="msg">{r.message}</td>
                <td className="reasons">
                  <ul>
                    {r.reasons.map((x, i) => (
                      <li key={i}>{x}</li>
                    ))}
                  </ul>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
