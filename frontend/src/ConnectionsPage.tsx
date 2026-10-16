import { useEffect, useState } from "react";
import { api, type ConnectorStatus, type Health } from "./api";
import type { ErrorHandler } from "./App";
import { NETWORK_LABELS } from "./labels";

export default function ConnectionsPage({ onError }: { onError: ErrorHandler }) {
  const [health, setHealth] = useState<Health | null>(null);
  const [connectors, setConnectors] = useState<ConnectorStatus[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.health(), api.connectors()])
      .then(([h, c]) => {
        setHealth(h);
        setConnectors(c);
      })
      .catch((e) => setError(onError(e)));
  }, [onError]);

  return (
    <>
      {error && <p className="error">{error}</p>}

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
    </>
  );
}
