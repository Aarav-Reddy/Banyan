"use client";
import Link from "next/link";
import { BanyanLogo } from "./banyan-logo";
import { useEffect, useState, useRef, createContext, useContext } from "react";
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
import {
  Form,
  Field,
  Notice,
  Header,
  Panel,
  Icon,
  PrintSupport,
  text,
} from "./ui";
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
  const menuButton = useRef<HTMLButtonElement>(null);
  const closeButton = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (!menu) return;
    closeButton.current?.focus();
    function escape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenu(false);
        menuButton.current?.focus();
      }
    }
    window.addEventListener("keydown", escape);
    return () => window.removeEventListener("keydown", escape);
  }, [menu]);
  function closeMenu() {
    setMenu(false);
    menuButton.current?.focus();
  }
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
          <BanyanLogo /> Banyan
        </a>
        {error ? (
          <Notice tone="error">Unable to connect to the API. {error}</Notice>
        ) : (
          <p role="status">Opening Banyan…</p>
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
            <BanyanLogo /> Banyan
          </Link>
          <nav>
            <Link href="/methodology">Methodology</Link>
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
            readOnly={!!session.demo_read_only}
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
          Banyan · Baltimore food security pilot{" "}
          <span>Financial context · Permissioned program evidence</span>
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
  const groups = [
    {
      title: donor ? "Funding work" : "Your programs & data",
      items: donor
        ? [
            ["discover", "organizations", "Organizations"],
            ["portfolios", "plans", "Funding plans"],
            ["allocate", "plan", "Plan funding"],
          ]
        : [
            ["dashboard", "overview", "Overview"],
            ["programs", "programs", "Programs"],
            ["uploads", "upload", "Data uploads"],
            ["impact-report", "report", "Impact report"],
          ],
    },
    {
      title: donor ? "Shared evidence" : "Learning & funding",
      items: [
        ["evidence", "evidence", "Evidence library"],
        ["saved", "saved", "Saved evidence"],
        ["analyses", "analysis", "Combined analysis"],
        ["graph", "connections", "Connections"],
        ...(!donor ? [["opportunities", "plan", "Funding opportunities"]] : []),
      ],
    },
    {
      title: "Monitoring",
      items: [
        ["watchlist", "watch", "Watchlist"],
        ["alerts", "alerts", "Alerts"],
        ...(ws.role === "reviewer" ? [["reviews", "review", "Reviews"]] : []),
      ],
    },
  ];
  const pageLabels: Record<string, string> = {
    discover: "Organizations",
    organizations: "Organization profile",
    compare: "Compare organizations",
    allocate: "Plan funding",
    portfolios: "Funding plans",
    uploads: "Data uploads",
    analyses: "Combined analysis",
    graph: "Connections",
    dashboard: "Overview",
    saved: "Saved evidence",
    evidence: "Evidence library",
    sharing: "Sharing & privacy",
    settings: "Workspace settings",
    reports: "Report",
    admin: "Data-use activity",
    audit: "Data-use activity",
    jobs: "Background jobs",
    metrics: "Pilot measurement",
    reviews: "Reviews",
    "impact-report": "Impact report",
    opportunities: "Funding opportunities",
  };
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
          <Link href="/discover">Return to organizations</Link>
        </Header>
      );
  }
  return (
    <WorkspaceContext.Provider value={ws}>
      <PrintSupport />
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <div className="app-shell">
        <aside
          id="workspace-navigation"
          className={`sidebar ${menu ? "open" : ""}`}
        >
          <div className="sidebar-brand">
            <Link className="brand" href={donor ? "/discover" : "/dashboard"}>
              <BanyanLogo /> Banyan
            </Link>
            <button
              type="button"
              ref={closeButton}
              className="mobile-close secondary"
              onClick={closeMenu}
              aria-label="Close navigation"
            >
              <Icon name="close" /> Close
            </button>
          </div>
          <p className="workspace-kind">
            {donor ? "Foundation workspace" : "Contributor workspace"}
          </p>
          <nav aria-label="Main navigation">
            {groups.map((group) => (
              <div className="nav-group" key={group.title}>
                <p className="nav-label">{group.title}</p>
                {group.items.map(([href, icon, name]) => (
                  <Link
                    key={href}
                    href={`/${href}`}
                    onClick={() => {
                      if (menu) closeMenu();
                    }}
                    aria-current={page === href ? "page" : undefined}
                  >
                    <Icon name={icon} />
                    {name}
                  </Link>
                ))}
              </div>
            ))}
          </nav>
          <div className="sidebar-bottom">
            <nav aria-label="Workspace utilities">
              <p className="nav-label">Workspace</p>
              {[
                ["sharing", "privacy", "Sharing & privacy"],
                ["settings", "settings", "Settings"],
                ["methodology", "info", "Methodology"],
              ].map(([href, icon, name]) => (
                <Link
                  key={href}
                  href={`/${href}`}
                  aria-current={page === href ? "page" : undefined}
                  onClick={() => {
                    if (menu) closeMenu();
                  }}
                >
                  <Icon name={icon} />
                  {name}
                </Link>
              ))}
            </nav>
            <div className="mode-note">
              Deterministic calculations
              <br />
              <small>Works without an AI provider</small>
            </div>
          </div>
        </aside>
        <div className="main-shell">
          <header className="topbar">
            <button
              type="button"
              ref={menuButton}
              className="mobile-menu secondary"
              onClick={() => (menu ? closeMenu() : setMenu(true))}
              aria-label={menu ? "Close navigation" : "Open navigation"}
              aria-expanded={menu}
              aria-controls="workspace-navigation"
            >
              <Icon name={menu ? "close" : "menu"} /> Menu
            </button>
            <div className="breadcrumbs">{pageLabels[page] || label(page)}</div>
            <div className="workspace-controls">
              <label className="workspace-caption" htmlFor="workspace">
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
              <strong>
                {session.demo_read_only
                  ? "Read-only demo."
                  : "Demo environment."}
              </strong>{" "}
              Fictional nonprofit organizations and synthetic program evidence.
              Public context is labeled separately. No money is moved.
            </div>
          )}
          {error && <Notice tone="error">{error}</Notice>}
          <main
            id="main"
            tabIndex={-1}
            className="workspace-main"
            key={selected + path.join("/")}
          >
            {content}
          </main>
          <footer className="app-footer">
            <span>Baltimore food security pilot</span>
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
      <section className="hero">
        <p className="eyebrow">Baltimore food security pilot</p>
        <h1>Research nonprofits and learn from shared evidence.</h1>
        <p className="hero-description">
          Compare nonprofit finances and plan funding. Share program evidence
          and learn from other nonprofits.
        </p>
        <div className="actions">
          <Link className="button primary" href={demo ? "/demo" : "/login"}>
            {demo ? "Explore the demo" : "Open your workspace"}{" "}
            <span aria-hidden="true">→</span>
          </Link>
          <Link className="button secondary" href="/methodology">
            Read the methodology
          </Link>
        </div>
        {demo && (
          <p className="pilot-disclosure">
            Demo organizations and program evidence are fictional. Public
            context is labeled separately. No money moves.
          </p>
        )}
      </section>
      <section className="audience-paths" aria-label="Two ways to use Banyan">
        <article>
          <p className="eyebrow">For foundations</p>
          <h2>Investigate a funding decision</h2>
          <ol>
            <li>Find organizations by cause and reported service area.</li>
            <li>Compare finances, evidence and missing information.</li>
            <li>Prepare a funding plan for human review.</li>
          </ol>
          <p className="fine">
            Financial warning signals guide investigation. They do not predict
            failure or measure impact.
          </p>
        </article>
        <article>
          <p className="eyebrow">For nonprofits</p>
          <h2>Learn from program experience</h2>
          <ol>
            <li>Describe your programs and upload aggregate data.</li>
            <li>Read shared evidence, including limitations and failures.</li>
            <li>Choose how your evidence is shared.</li>
          </ol>
          <p className="fine">
            Context matches are questions to investigate, not endorsements or
            proof an intervention will transfer.
          </p>
        </article>
      </section>
    </main>
  );
}
function Login({
  demo,
  readOnly,
  onLogin,
  join,
}: {
  demo: boolean;
  readOnly: boolean;
  onLogin: (s: Session) => void;
  join: boolean;
}) {
  return (
    <main className="login-layout">
      <div>
        <p className="eyebrow">Baltimore food security pilot</p>
        <h1>{join ? "Join a workspace" : "Sign in to Banyan"}</h1>
        <p>
          {join
            ? "Use your invitation token to join the workspace that invited you."
            : "Open your foundation or nonprofit workspace to continue your research."}
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
            <h3>Demo sign-in credentials</h3>
            {readOnly && (
              <p className="fine">
                This public demo is read-only. You can browse with any role;
                changes, uploads, and approvals are disabled.
              </p>
            )}
            <div className="table-wrap">
              <table aria-label="Demo sign-in credentials">
                <thead>
                  <tr>
                    <th scope="col">Username</th>
                    <th scope="col">Password</th>
                  </tr>
                </thead>
                <tbody>
                  {["foundation-admin", "ngo-owner", "reviewer"].map((user) => (
                    <tr key={user}>
                      <td>{user}</td>
                      <td>Demo-only-Banyan-2026!</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <h3>Explore with a demo role</h3>
            <p className="fine">Choose a role to try the existing workflows.</p>
            {[
              ["foundation-admin", "Foundation administrator"],
              ["ngo-owner", "Nonprofit owner"],
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
                      password: "Demo-only-Banyan-2026!",
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
