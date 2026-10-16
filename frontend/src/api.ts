export type Health = { status: string; scheduler_running: boolean };

export type AuthStatus = { auth_enabled: boolean; logged_in: boolean };

export type ConnectorStatus = {
  network: string;
  configured: boolean;
  ok: boolean;
  detail: string;
  account: string | null;
};

export type PostStatus = "draft" | "scheduled" | "publishing" | "published" | "failed";

export type Media = { id: number; kind: "photo" | "video" | "document"; url: string };

export type Publication = {
  network: string;
  status: "pending" | "sent" | "failed";
  url: string | null;
  error: string | null;
  published_at: string | null;
};

export type Post = {
  id: number;
  body: string;
  language: string;
  status: PostStatus;
  targets: string[];
  scheduled_at: string | null;
  created_at: string;
  updated_at: string;
  media: Media[];
  publications: Publication[];
};

export type PostInput = { body: string; language: string; targets?: string[] };

/** Thrown when the backend says we need to log in. */
export class Unauthorized extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, init);
  if (res.status === 401 && path !== "/api/login") throw new Unauthorized("Log in first.");
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(typeof body?.detail === "string" ? body.detail : `${path}: ${res.status}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

const json = (method: string, body?: unknown): RequestInit => ({
  method,
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const api = {
  health: () => request<Health>("/api/health"),
  auth: () => request<AuthStatus>("/api/auth"),
  login: (password: string) => request<{ ok: boolean }>("/api/login", json("POST", { password })),
  logout: () => request<{ ok: boolean }>("/api/logout", json("POST")),
  connectors: () => request<ConnectorStatus[]>("/api/connectors"),

  posts: () => request<Post[]>("/api/posts"),
  post: (id: number) => request<Post>(`/api/posts/${id}`),
  createPost: (data: PostInput) => request<Post>("/api/posts", json("POST", data)),
  updatePost: (id: number, data: Partial<PostInput>) => request<Post>(`/api/posts/${id}`, json("PATCH", data)),
  deletePost: (id: number) => request<void>(`/api/posts/${id}`, { method: "DELETE" }),
  publish: (id: number) => request<Post>(`/api/posts/${id}/publish`, json("POST")),
  uploadMedia: (id: number, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<Post>(`/api/posts/${id}/media`, { method: "POST", body: form });
  },
  deleteMedia: (id: number, mediaId: number) =>
    request<Post>(`/api/posts/${id}/media/${mediaId}`, { method: "DELETE" }),
};
