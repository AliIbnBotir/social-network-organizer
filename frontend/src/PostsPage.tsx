import { useEffect, useState } from "react";
import { api, type Post, type PostStatus } from "./api";
import type { ErrorHandler } from "./App";
import { formatDate, NETWORK_LABELS, STATUS_LABELS } from "./labels";

const FILTERS: { label: string; status: PostStatus | null }[] = [
  { label: "All", status: null },
  { label: "Drafts", status: "draft" },
  { label: "Published", status: "published" },
  { label: "Failed", status: "failed" },
];

export default function PostsPage({ onError }: { onError: ErrorHandler }) {
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [filter, setFilter] = useState<PostStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.posts().then(setPosts, (e) => setError(onError(e)));
  }, [onError]);

  const remove = async (post: Post) => {
    const sent = post.publications.some((p) => p.status === "sent");
    const question = sent
      ? "Delete this post from the organizer? It stays in your channel."
      : "Delete this draft?";
    if (!window.confirm(question)) return;
    try {
      await api.deletePost(post.id);
      setPosts((all) => all?.filter((p) => p.id !== post.id) ?? null);
    } catch (e) {
      setError(onError(e));
    }
  };

  const shown = posts?.filter((p) => filter === null || p.status === filter);

  return (
    <section>
      <div className="posts-header">
        <h2>Posts</h2>
        <div className="filters">
          {FILTERS.map((f) => (
            <button key={f.label} className={filter === f.status ? "active" : ""} onClick={() => setFilter(f.status)}>
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {!posts && !error && <p className="muted">Loading…</p>}
      {shown?.length === 0 && (
        <p className="muted">
          Nothing here yet. <a href="#/write">Write a post</a>.
        </p>
      )}

      <ul className="posts">
        {shown?.map((post) => (
          <li key={post.id} className="card">
            <div className="post-meta">
              <span className={`badge ${post.status}`}>{STATUS_LABELS[post.status]}</span>
              <span className="muted">
                {post.language.toUpperCase()} · {formatDate(post.updated_at)}
                {post.media.length > 0 && ` · ${post.media.length} media`}
              </span>
            </div>
            <p className="post-body">{post.body.length > 280 ? `${post.body.slice(0, 280)}…` : post.body || <em>No text</em>}</p>
            {post.publications.map((p) => (
              <p key={p.network} className={p.status === "failed" ? "error" : "muted"}>
                {NETWORK_LABELS[p.network] ?? p.network}:{" "}
                {p.status === "sent" ? (
                  p.url ? <a href={p.url} target="_blank" rel="noreferrer">view post</a> : "sent"
                ) : (
                  p.error ?? p.status
                )}
              </p>
            ))}
            <div className="actions">
              {(post.status === "draft" || post.status === "failed") && (
                <a className="button" href={`#/write/${post.id}`}>
                  {post.status === "failed" ? "Edit or retry" : "Edit"}
                </a>
              )}
              {post.status !== "publishing" && (
                <button className="link danger" onClick={() => remove(post)}>Delete</button>
              )}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
