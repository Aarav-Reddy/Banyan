"use client";
import Link from "next/link";
import { useEffect, useState, createContext, useContext } from "react";
import { useRouter } from "next/navigation";
import {
  Session,
  Workspace,
  api,
  configureSession,
  selectWorkspace,
  mutate,
  label,
} from "@/lib/api";
import { Form, Field, Notice, Header, Panel, text } from "./ui";
import {
  Discovery,
  Organization,
  Compare,
  Allocation,
  Portfolios,
  Portfolio,
} from "./donor";
import {
  Dashboard,
  Programs,
  ProgramEditor,
  Cards,
  Card,
  CardEditor,
  Uploads,
  ImportDetail,
  Opportunities,
} from "./ngo";
import {
  Analyses,
  Graph,
  Alerts,
  Sharing,
  SourcesPage,
  Settings,
  Reviews,
  Metrics,
  Methodology,
  Jobs,
  Report,
  Audit,
} from "./shared";
import {
  PasswordReset,
  SavedEvidence,
  Watchlist,
  ImpactReport,
  CreateWorkspace,
} from "./pilot";
const WorkspaceContext = createContext<Workspace>({
  id: "",
  name: "",
  kind: "",
  role: "",
  organization_id: null,
});
export const useWorkspace = () => useContext(WorkspaceContext);
export function Application({ path }: { path: string[] }) {
  const [session, setSession] = useState<Session | null>(null),
    [error, setError] = useState(""),
    [selected, setSelected] = useState(""),
    [menu, setMenu] = useState(false);
  const router = useRouter();
  useEffect(() => {
    api<Session>("session/")
      .then((s) => {
        configureSession(s);
        setSession(s);
        setSelected(s.workspaces[0]?.id || "");
      })
      .catch((e) => setError(e.message));
  }, []);
  useEffect(() => {
    const refresh = (event: Event) => {
      const id = (event as CustomEvent<string>).detail;
      api<Session>("session/")
        .then((s) => {
          const selectedId = s.workspaces.some((w) => w.id === id)
            ? id
            : s.workspaces[0]?.id || "";
          configureSession(s, selectedId);
          setSession(s);
          setSelected(selectedId);
          router.push("/settings");
        })
        .catch((e) => setError(e.message));
    };
    window.addEventListener("philanthra:workspace-created", refresh);
    return () =>
      window.removeEventListener("philanthra:workspace-created", refresh);
  }, [router]);
  const ws = session?.workspaces.find((w) => w.id === selected);
  const page = path[0] || "";
  function signedIn(s: Session) {
    configureSession(s);
    setSession(s);
    setSelected(s.workspaces[0]?.id || "");
    router.push(
      s.workspaces[0]?.kind === "ngo"
        ? "/dashboard"
        : s.workspaces[0]?.role === "reviewer"
          ? "/reviews"
          : "/discover",
    );
  }
  if (!session)
    return (
      <main className="boot">
        <a className="brand" href="/">
          ◈ Philanthra
        </a>
        {error ? (
          <Notice tone="error">Unable to connect to the API. {error}</Notice>
        ) : (
          <p role="status">Opening Philanthra…</p>
        )}
      </main>
    );
  if (
    !session.user ||
    !page ||
    page === "login" ||
    page === "demo" ||
    page === "join" ||
    page === "password-reset"
  )
    return (
      <div className="public-shell">
        <header className="public-header">
          <Link className="brand" href="/">
            ◈ Philanthra
          </Link>
          <nav>
            <Link href="/methodology">Our methodology</Link>
            {session.user ? (
              <Link className="button primary" href="/discover">
                Open workspace →
              </Link>
            ) : (
              <Link className="button secondary" href="/login">
                Sign in
              </Link>
            )}
          </nav>
        </header>
        {page === "password-reset" ? (
          <PasswordReset />
        ) : ["login", "demo", "join"].includes(page) ||
          (!session.user && page && page !== "methodology") ? (
          <Login
            demo={!!session.demo_mode}
            onLogin={signedIn}
            join={page === "join"}
          />
        ) : page === "methodology" ? (
          <main className="public-content">
            <Methodology />
          </main>
        ) : (
          <Landing demo={!!session.demo_mode} />
        )}
        <footer className="public-footer">
          Philanthra · Baltimore food security pilot{" "}
          <span>Evidence with context. Decisions with care.</span>
        </footer>
      </div>
    );
  if (!ws)
    return (
      <main className="boot">
        <Notice>
          No workspace membership is available. Ask your workspace owner for a
          scoped invitation.
        </Notice>
        <CreateWorkspace />
      </main>
    );
  const donor = ws.kind === "foundation";
  const items = [
    ...(donor
      ? [
          ["discover", "◎", "Discover organizations"],
          ["portfolios", "▤", "Saved portfolios"],
          ["allocate", "↗", "Allocation workbench"],
        ]
      : [
          ["dashboard", "▦", "Overview"],
          ["programs", "▤", "Programs"],
          ["uploads", "↑", "Data & uploads"],
        ]),
    ["evidence", "◇", "Evidence library"],
    ["saved", "▤", "Saved evidence"],
    ["watchlist", "◎", "Watchlist"],
    ...(!donor ? [["impact-report", "▤", "Impact report"]] : []),
    ["analyses", "◫", "Pooled analysis"],
    ["graph", "⌘", "Knowledge graph"],
    ...(!donor ? [["opportunities", "↗", "Funding opportunities"]] : []),
    ["alerts", "◷", "Alerts"],
    ...(ws.role === "reviewer" ? [["reviews", "✓", "Review workbench"]] : []),
  ];
  let content: React.ReactNode;
  switch (page) {
    case "saved":
      content = <SavedEvidence />;
      break;
    case "watchlist":
      content = <Watchlist />;
      break;
    case "impact-report":
      content = <ImpactReport />;
      break;
    case "discover":
      content = <Discovery />;
      break;
    case "organizations":
      content = <Organization id={path[1]} />;
      break;
    case "compare":
      content = <Compare />;
      break;
    case "allocate":
      content = <Allocation />;
      break;
    case "portfolios":
      content = path[1] ? <Portfolio id={path[1]} /> : <Portfolios />;
      break;
    case "dashboard":
      content = <Dashboard />;
      break;
    case "programs":
      content =
        path[1] === "new" || path[1] ? (
          <ProgramEditor id={path[1] === "new" ? undefined : path[1]} />
        ) : (
          <Programs />
        );
      break;
    case "evidence":
      content =
        path[1] === "new" ? (
          <CardEditor />
        ) : path[2] === "edit" ? (
          <CardEditor id={path[1]} />
        ) : path[1] ? (
          <Card id={path[1]} />
        ) : (
          <Cards />
        );
      break;
    case "uploads":
      content = path[1] ? <ImportDetail id={path[1]} /> : <Uploads />;
      break;
    case "analyses":
      content = <Analyses />;
      break;
    case "graph":
      content = <Graph />;
      break;
    case "alerts":
      content = <Alerts />;
      break;
    case "opportunities":
      content = <Opportunities />;
      break;
    case "sharing":
      content = <Sharing />;
      break;
    case "sources":
      content = <SourcesPage id={path[1]} />;
      break;
    case "settings":
      content = <Settings />;
      break;
    case "reviews":
      content = <Reviews />;
      break;
    case "metrics":
      content = <Metrics />;
      break;
    case "methodology":
      content = <Methodology />;
      break;
    case "jobs":
      content = <Jobs />;
      break;
    case "reports":
      content = <Report id={path[1]} />;
      break;
    case "audit":
    case "admin":
      content = <Audit />;
      break;
    default:
      content = (
        <Header title="Page not found">
          <Link href="/discover">Return to discovery</Link>
        </Header>
      );
  }
  return (
    <WorkspaceContext.Provider value={ws}>
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <div className="app-shell">
        <aside className={`sidebar ${menu ? "open" : ""}`}>
          <Link className="brand" href={donor ? "/discover" : "/dashboard"}>
            <span>◈</span> Philanthra
          </Link>
          <p className="nav-label">
            {donor ? "Foundation workspace" : "Contributor workspace"}
          </p>
          <nav aria-label="Main navigation">
            {items.map(([href, icon, name]) => (
              <Link
                key={href}
                href={`/${href}`}
                onClick={() => setMenu(false)}
                aria-current={page === href ? "page" : undefined}
              >
                <span aria-hidden="true">{icon}</span>
                {name}
              </Link>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <Link href="/sharing">◉ Sharing & privacy</Link>
            <Link href="/settings">⚙ Workspace settings</Link>
            <Link href="/methodology">ⓘ Methodology</Link>
            <div className="mode-note">
              <span className="dot" /> Deterministic engine
              <br />
              <small>Works without an AI provider</small>
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <button
              className="mobile-menu"
              onClick={() => setMenu(!menu)}
              aria-label="Toggle navigation"
              aria-expanded={menu}
            >
              ☰
            </button>
            <div className="breadcrumbs">
              Workspace <span>/</span> {label(page)}
            </div>
            <div className="workspace-controls">
              <label className="sr-only" htmlFor="workspace">
                Active workspace
              </label>
              <select
                id="workspace"
                value={selected}
                onChange={(e) => {
                  selectWorkspace(e.target.value);
                  setSelected(e.target.value);
                }}
              >
                {session.workspaces.map((w) => (
                  <option value={w.id} key={w.id}>
                    {w.name}
                  </option>
                ))}
              </select>
              <span className="avatar" title={session.user.username}>
                {session.user.username.slice(0, 2).toUpperCase()}
              </span>
              <button
                className="text-button"
                onClick={async () => {
                  try {
                    await mutate("logout/", "POST");
                    const s = await api<Session>("session/");
                    configureSession(s);
                    setSession(s);
                    router.push("/login");
                  } catch (e) {
                    setError((e as Error).message);
                  }
                }}
              >
                Sign out
              </button>
            </div>
          </header>
          {session.demo_mode && (
            <div className="demo-banner">
              <span>DEMO ENVIRONMENT</span> Fictional nonprofit organizations
              and synthetic program evidence. Public context is labeled
              separately. No money is moved.
            </div>
          )}
          {error && <Notice tone="error">{error}</Notice>}
          <main
            id="main"
            className="workspace-main"
            key={selected + path.join("/")}
          >
            {content}
          </main>
          <footer className="app-footer">
            <span>Built for thoughtful decisions, informed by evidence.</span>
            <Link href="/sources">Source registry</Link>
            <Link href="/metrics">Pilot measurement</Link>
          </footer>
        </div>
      </div>
    </WorkspaceContext.Provider>
  );
}
function Landing({ demo }: { demo: boolean }) {
  return (
    <main className="landing">
      <div className="hero">
        <div>
          <p className="eyebrow">A shared foundation for better decisions</p>
          <h1>
            Better giving starts
            <br />
            with better evidence.
          </h1>
          <p className="hero-description">
            Connect where funding is needed with what nonprofits are learning.
            Explore financial context, learn from shared evidence, and plan your
            next step with care.
          </p>
          <div className="actions">
            <Link className="button primary" href={demo ? "/demo" : "/login"}>
              {demo ? "Explore the pilot" : "Open your workspace"} →
            </Link>
            <Link className="button secondary" href="/methodology">
              How Philanthra works
            </Link>
          </div>
          <p className="fine">
            Starting with food security in the Baltimore region.
          </p>
        </div>
        <div
          className="hero-visual"
          aria-label="Philanthra connects organizations, context, evidence and funding"
        >
          <div className="visual-label">THE SHARED PICTURE</div>
          <div className="orbit">
            <div className="orbit-center">
              ◈<strong>Philanthra</strong>
              <small>Evidence in context</small>
            </div>
            <span className="orbit-node n1">◎ Organizations</span>
            <span className="orbit-node n2">◇ Program evidence</span>
            <span className="orbit-node n3">◫ Community context</span>
            <span className="orbit-node n4">↗ Funding decisions</span>
          </div>
          <p>
            Every insight has a source.
            <br />
            Every decision stays human.
          </p>
        </div>
      </div>
      <div className="landing-columns">
        <article>
          <span className="step">01 / FOR FOUNDATIONS</span>
          <h2>Find where to investigate.</h2>
          <p>
            Compare organizations, understand financial warning signals, and
            create transparent funding plans for human review.
          </p>
        </article>
        <article>
          <span className="step">02 / FOR NONPROFITS</span>
          <h2>Learn before you act.</h2>
          <p>
            Contribute aggregate program evidence, explore lessons from peers,
            and control exactly how your data are shared.
          </p>
        </article>
        <article>
          <span className="step">03 / FOR SHARED LEARNING</span>
          <h2>See the wider picture.</h2>
          <p>
            Bring compatible observations together. Keep context, missing
            information, and uncertainty visible.
          </p>
        </article>
      </div>
    </main>
  );
}
function Login({
  demo,
  onLogin,
  join,
}: {
  demo: boolean;
  onLogin: (s: Session) => void;
  join: boolean;
}) {
  return (
    <main className="login-layout">
      <div>
        <p className="eyebrow">Welcome to Philanthra</p>
        <h1>
          Good decisions.
          <br />
          Shared knowledge.
        </h1>
        <p>
          Choose a workspace to investigate funding or turn program experience
          into useful evidence.
        </p>
        {demo && (
          <Notice>
            Isolated demo · All organizations and reported outcomes are
            fictional. Approvals by demo accounts are demonstration events.
          </Notice>
        )}
      </div>
      <Panel
        title={join ? "Redeem your invitation" : "Sign in to your workspace"}
      >
        <Form
          submit={join ? "Join workspace" : "Sign in"}
          onSubmit={async (f) =>
            onLogin(
              await mutate<Session>(
                join ? "invitations/redeem/" : "login/",
                "POST",
                {
                  username: text(f, "username"),
                  password: text(f, "password"),
                  ...(join ? { token: text(f, "token") } : {}),
                },
              ),
            )
          }
        >
          {join && <Field label="Invitation token" name="token" required />}
          <Field
            label="Username"
            name="username"
            autoComplete="username"
            required
          />
          <Field
            label="Password"
            name="password"
            type="password"
            autoComplete={join ? "new-password" : "current-password"}
            required
          />
        </Form>
        <p className="fine">
          {join ? (
            <Link href="/login">Already a member? Sign in</Link>
          ) : (
            <Link href="/join">Have an invitation? Join a workspace</Link>
          )}
        </p>
        {!join && (
          <p>
            <Link href="/password-reset">Forgot your password?</Link>
          </p>
        )}
        {demo && !join && (
          <div className="demo-roles">
            <p className="eyebrow">Or enter as a demo role</p>
            {[
              ["foundation-admin", "Foundation administrator"],
              ["ngo-owner", "NGO owner"],
              ["reviewer", "Assigned reviewer"],
              ["foundation-viewer", "Read-only foundation viewer"],
            ].map(([user, caption]) => (
              <Form
                key={user}
                className="role-form"
                submit={`${caption} →`}
                success="Opening workspace…"
                onSubmit={async () =>
                  onLogin(
                    await mutate<Session>("login/", "POST", {
                      username: user,
                      password: "Demo-only-Philanthra-2026!",
                    }),
                  )
                }
              >
                {null}
              </Form>
            ))}
          </div>
        )}
      </Panel>
    </main>
  );
}
