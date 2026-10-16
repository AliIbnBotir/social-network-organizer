import { useCallback, useEffect, useState } from "react";
import { api, Unauthorized, type AuthStatus } from "./api";
import ConnectionsPage from "./ConnectionsPage";
import LoginPage from "./LoginPage";
import PostsPage from "./PostsPage";
import WritePage from "./WritePage";

/** Turns an API error into a message, sending the user to the login page on 401. */
export type ErrorHandler = (e: unknown) => string;

function useHashRoute(): string {
  const [hash, setHash] = useState(window.location.hash || "#/");
  useEffect(() => {
    const onChange = () => setHash(window.location.hash || "#/");
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return hash;
}

export default function App() {
  const route = useHashRoute();
  const [auth, setAuth] = useState<AuthStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.auth().then(setAuth, (e: Error) => setError(e.message));
  }, []);

  const handleError: ErrorHandler = useCallback((e) => {
    if (e instanceof Unauthorized) setAuth((a) => (a ? { ...a, logged_in: false } : a));
    return e instanceof Error ? e.message : String(e);
  }, []);

  if (error) return <main><p className="error">Can't reach the backend: {error}</p></main>;
  if (!auth) return <main><p className="muted">Loading…</p></main>;
  if (!auth.logged_in) return <LoginPage onLogin={() => setAuth({ ...auth, logged_in: true })} />;

  const editMatch = route.match(/^#\/write\/(\d+)$/);
  let page;
  if (route === "#/write" || editMatch) {
    const postId = editMatch ? Number(editMatch[1]) : null;
    page = <WritePage key={postId ?? "new"} postId={postId} onError={handleError} />;
  } else if (route === "#/posts") {
    page = <PostsPage onError={handleError} />;
  } else {
    page = <ConnectionsPage onError={handleError} />;
  }

  const logout = () => api.logout().then(() => setAuth({ ...auth, logged_in: false }));
  const current = route.startsWith("#/write") ? "#/write" : route;

  return (
    <main>
      <header>
        <h1>Social Network Organizer</h1>
        <nav>
          <a href="#/write" className={current === "#/write" ? "active" : ""}>Write</a>
          <a href="#/posts" className={current === "#/posts" ? "active" : ""}>Posts</a>
          <a href="#/" className={current === "#/" ? "active" : ""}>Connections</a>
          <span className="soon">Queue</span>
          <span className="soon">Analytics</span>
          {auth.auth_enabled && (
            <button className="link" onClick={logout}>Log out</button>
          )}
        </nav>
      </header>
      {!auth.auth_enabled && (
        <p className="warning">
          No password is set. Set DASHBOARD_PASSWORD before putting this app on the internet.
        </p>
      )}
      {page}
    </main>
  );
}
