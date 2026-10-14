import { useEffect, useState } from "react";
import { api, type ConnectorStatus, type Health } from "./api";

const NETWORK_LABELS: Record<string, string> = { telegram: "Telegram channel" };

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [connectors, setConnectors] = useState<ConnectorStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.connectors()])
      .then(([h, c]) => {
        setHealth(h);
        setConnectors(c);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <main>
      <header>
        <h1>Social Network Organizer</h1>
        <nav>
          {/* Filled in by the next steps. */}
          <span className="soon">Write</span>
          <span className="soon">Queue</span>
          <span className="soon">Analytics</span>
        </nav>
      </header>

      {error && <p className="error">Can't reach the backend: {error}</p>}

      <section>
        <h2>Connections</h2>
        {!connectors && !error && <p>Checking…</p>}
        <ul className="connectors">
          {connectors?.map((c) => (
            <li key={c.network} className={c.ok ? "ok" : "bad"}>
              <strong>{NETWORK_LABELS[c.network] ?? c.network}</strong>
              {c.account && <span>{c.account}</span>}
              <span>{c.detail}</span>
            </li>
          ))}
        </ul>
      </section>

      {health && (
        <p className="muted">
          Backend {health.status}, scheduler {health.scheduler_running ? "running" : "stopped"}.
        </p>
      )}
    </main>
  );
}
