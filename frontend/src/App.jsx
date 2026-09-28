import { useState } from "react";
import ChatPanel from "./components/ChatPanel";
import AdminDesk from "./components/AdminDesk";
import PolicyView from "./components/PolicyView";
import "./App.css";

const TABS = [
  { id: "support", label: "Support" },
  { id: "desk", label: "Desk" },
  { id: "policy", label: "Policy" },
];

export default function App() {
  const [tab, setTab] = useState("support");

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">N</span>
          <div>
            <strong>Northline</strong>
            <span className="brand-sub"> Care</span>
          </div>
        </div>
        <nav className="tabs">
          {TABS.map((t) => (
            <button
              key={t.id}
              className={tab === t.id ? "tab active" : "tab"}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
      </header>

      <main className="main">
        {tab === "support" && <ChatPanel />}
        {tab === "desk" && <AdminDesk />}
        {tab === "policy" && <PolicyView />}
      </main>

      <footer className="footer">
        Policy is applied in code first. NVIDIA writes the reply and classifies
        intent — it cannot approve a denied request.
      </footer>
    </div>
  );
}
