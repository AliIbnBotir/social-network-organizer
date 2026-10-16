import { useEffect, useRef, useState } from "react";
import { api, type Post } from "./api";
import type { ErrorHandler } from "./App";
import { CAPTION_LIMIT, LANGUAGES, MEDIA_LIMIT, TEXT_LIMIT } from "./labels";

type Props = { postId: number | null; onError: ErrorHandler };

export default function WritePage({ postId, onError }: Props) {
  const [post, setPost] = useState<Post | null>(null);
  const [body, setBody] = useState("");
  const [language, setLanguage] = useState("uz");
  const [loading, setLoading] = useState(postId !== null);
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInput = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (postId === null) return;
    api
      .post(postId)
      .then((p) => {
        setPost(p);
        setBody(p.body);
        setLanguage(p.language);
      })
      .catch((e) => setError(onError(e)))
      .finally(() => setLoading(false));
  }, [postId, onError]);

  const reset = () => {
    setPost(null);
    setBody("");
    setMessage(null);
    setError(null);
  };

  // Clicking "Write" while editing a post starts a new one. (Saving a new
  // draft only rewrites the URL, so it doesn't fire hashchange.)
  useEffect(() => {
    const onChange = () => {
      if (window.location.hash === "#/write") reset();
    };
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);

  const media = post?.media ?? [];
  const dirty = !post || post.body !== body || post.language !== language;
  const editable = !post || post.status === "draft" || post.status === "failed";
  const published = post?.status === "published";

  const tooLong = body.length > TEXT_LIMIT;
  const captionSplit = media.length > 0 && body.length > CAPTION_LIMIT && !tooLong;
  const mixesDocuments =
    media.length > 1 && media.some((m) => m.kind === "document") && media.some((m) => m.kind !== "document");
  const empty = !body.trim() && media.length === 0;

  /** Save edits, creating the draft first if needed. Returns the saved post. */
  const save = async (): Promise<Post> => {
    if (!post) {
      const created = await api.createPost({ body, language });
      setPost(created);
      window.history.replaceState(null, "", `#/write/${created.id}`);
      return created;
    }
    if (!dirty) return post;
    const updated = await api.updatePost(post.id, { body, language });
    setPost(updated);
    return updated;
  };

  const run = async (label: string, action: () => Promise<void>) => {
    setBusy(label);
    setError(null);
    setMessage(null);
    try {
      await action();
    } catch (e) {
      setError(onError(e));
    } finally {
      setBusy(null);
    }
  };

  const saveDraft = () =>
    run("save", async () => {
      await save();
      setMessage("Draft saved.");
    });

  const addFiles = (files: FileList | null) =>
    run("upload", async () => {
      if (!files?.length) return;
      let current = await save();
      for (const file of Array.from(files)) {
        if (current.media.length >= MEDIA_LIMIT) {
          throw new Error(`A post can have at most ${MEDIA_LIMIT} images or videos.`);
        }
        current = await api.uploadMedia(current.id, file);
        setPost(current);
      }
    }).finally(() => {
      if (fileInput.current) fileInput.current.value = "";
    });

  const removeMedia = (mediaId: number) =>
    run("remove", async () => {
      if (post) setPost(await api.deleteMedia(post.id, mediaId));
    });

  const publish = () => {
    if (!window.confirm("Publish this post to your Telegram channel now?")) return;
    return run("publish", async () => {
      const saved = await save();
      const result = await api.publish(saved.id);
      setPost(result);
      if (result.status !== "published") {
        const failure = result.publications.find((p) => p.status === "failed");
        throw new Error(`Publishing failed: ${failure?.error ?? "unknown error"}`);
      }
    });
  };

  if (loading) return <p className="muted">Loading…</p>;

  if (published && post) {
    const link = post.publications.find((p) => p.url)?.url;
    return (
      <section className="card">
        <h2>Published</h2>
        <p className="post-body">{post.body}</p>
        {link ? (
          <p><a href={link} target="_blank" rel="noreferrer">Open it in your channel</a></p>
        ) : (
          <p className="muted">Sent to your channel.</p>
        )}
        <button
          className="primary"
          onClick={() => {
            reset();
            window.history.replaceState(null, "", "#/write");
          }}
        >
          Write another
        </button>
      </section>
    );
  }

  return (
    <section className="write">
      <h2>{post ? `Post #${post.id}` : "New post"}</h2>
      {!editable && post && <p className="warning">This post is {post.status} and can't be changed.</p>}

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        placeholder="What's on your mind?"
        rows={10}
        disabled={!editable}
        autoFocus
      />
      <div className="counter-row">
        <select value={language} onChange={(e) => setLanguage(e.target.value)} disabled={!editable}>
          {Object.entries(LANGUAGES).map(([code, label]) => (
            <option key={code} value={code}>{label}</option>
          ))}
        </select>
        <span className={tooLong ? "error" : "muted"}>
          {body.length} / {TEXT_LIMIT}
        </span>
      </div>
      {tooLong && <p className="error">Telegram allows at most {TEXT_LIMIT} characters.</p>}
      {captionSplit && (
        <p className="muted">
          Over {CAPTION_LIMIT} characters, so the text will be sent as its own message right after the media.
        </p>
      )}
      {mixesDocuments && (
        <p className="warning">Telegram can't put files in the same album as photos or videos. Remove one kind.</p>
      )}

      {media.length > 0 && (
        <ul className="media">
          {media.map((m) => (
            <li key={m.id}>
              {m.kind === "photo" && <img src={m.url} alt="" />}
              {m.kind === "video" && <video src={m.url} muted />}
              {m.kind === "document" && <span className="file">File</span>}
              {editable && (
                <button className="remove" onClick={() => removeMedia(m.id)} disabled={!!busy} title="Remove">
                  ×
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {editable && (
        <div className="actions">
          <input
            ref={fileInput}
            type="file"
            accept="image/*,video/*"
            multiple
            hidden
            onChange={(e) => addFiles(e.target.files)}
          />
          <button onClick={() => fileInput.current?.click()} disabled={!!busy || media.length >= MEDIA_LIMIT}>
            {busy === "upload" ? "Uploading…" : "Add photo or video"}
          </button>
          <span className="spacer" />
          <button onClick={saveDraft} disabled={!!busy || (!dirty && !!post)}>
            {busy === "save" ? "Saving…" : "Save draft"}
          </button>
          <button className="primary" onClick={publish} disabled={!!busy || empty || tooLong || mixesDocuments}>
            {busy === "publish" ? "Publishing…" : "Publish now"}
          </button>
        </div>
      )}

      {message && <p className="ok-text">{message}</p>}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
