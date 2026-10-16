export type Health = { status: string; scheduler_running: boolean };

export type ConnectorStatus = {
  network: string;
  configured: boolean;
  ok: boolean;
  detail: string;
  account: string | null;
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path}: ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<Health>("/api/health"),
  connectors: () => get<ConnectorStatus[]>("/api/connectors"),
};
