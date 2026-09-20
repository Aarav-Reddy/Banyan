"use client";
import Link from "next/link";
import { useEffect, useState, ReactNode, FormEvent } from "react";
import { api, Row, label, date, download, mutate } from "@/lib/api";
export function useResource<T = Row>(path: string, version = 0) {
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setData(null);
    setError("");
    api<T>(path)
      .then((d) => {
        if (active) setData(d);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [path, version]);
  return { data, error };
}
export function Notice({
  children,
  tone = "info",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return (
    <div
      className={`notice ${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      {children}
    </div>
  );
}
export function State({
  error,
  data,
  children,
}: {
  error: string;
  data: unknown;
  children: ReactNode;
}) {
  if (error)
    return (
      <Notice tone="error">
        {error}{" "}
        <span>Try refreshing, or check your workspace and source access.</span>
      </Notice>
    );
  if (data === null)
    return (
      <div className="loading" role="status">
        Loading workspace records…
      </div>
    );
  return <>{children}</>;
}
export function Empty({
  title = "No records yet",
  children,
}: {
  title?: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <Icon name="evidence" />
      <h3>{title}</h3>
      <p>
        {children ||
          "Records will appear here when available and permitted for your workspace."}
      </p>
    </div>
  );
}
export function Badge({ children }: { children: unknown }) {
  const s = String(children ?? "unknown");
  return <span className={`badge ${s.replaceAll(" ", "_")}`}>{label(s)}</span>;
}
export function Header({
  eyebrow,
  title,
  children,
  action,
}: {
  eyebrow?: string;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {children && <div className="lede">{children}</div>}
      </div>
      {action}
    </header>
  );
}
export function Panel({
  title,
  children,
  aside,
  className = "",
  variant,
}: {
  title?: string;
  children: ReactNode;
  aside?: ReactNode;
  className?: string;
  variant?: "open";
}) {
  return (
    <section
      className={`panel ${variant === "open" ? "panel-open" : ""} ${className}`}
    >
      {title && (
        <div className="panel-heading">
          <h2>{title}</h2>
          {aside}
        </div>
      )}
      {children}
    </section>
  );
}
export function Field({
  label: caption,
  name,
  type = "text",
  value,
  required = false,
  children,
  hint,
  ...rest
}: {
  label: string;
  name: string;
  type?: string;
  value?: string | number;
  required?: boolean;
  children?: ReactNode;
  hint?: string;
  [key: string]: unknown;
}) {
  return (
    <label className="field">
      <span>{caption}</span>
      {children || (
        <input
          name={name}
          type={type}
          defaultValue={value}
          required={required}
          {...rest}
        />
      )}
      {hint && <small>{hint}</small>}
    </label>
  );
}
export function Textarea({
  label: caption,
  name,
  value = "",
  required = false,
}: {
  label: string;
  name: string;
  value?: string;
  required?: boolean;
}) {
  return (
    <Field label={caption} name={name}>
      <textarea name={name} defaultValue={value} required={required} rows={3} />
    </Field>
  );
}
export function Form({
  onSubmit,
  children,
  submit = "Save changes",
  className = "form",
  success = "Saved.",
}: {
  onSubmit: (form: FormData) => Promise<unknown>;
  children: ReactNode;
  submit?: string;
  className?: string;
  success?: string;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [message, setMessage] = useState("");
  async function run(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await onSubmit(new FormData(e.currentTarget));
      setMessage(success);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <form className={className} onSubmit={run}>
      {children}
      {error && <Notice tone="error">{error}</Notice>}
      {message && <Notice tone="success">{message}</Notice>}
      <button disabled={busy} type="submit" className="primary">
        {busy ? "Working…" : submit}
      </button>
    </form>
  );
}
export function Action({
  children,
  run,
  danger = false,
}: {
  children: ReactNode;
  run: () => Promise<unknown>;
  danger?: boolean;
}) {
  const [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  return (
    <>
      <button
        type="button"
        className={danger ? "danger" : "secondary"}
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          setError("");
          try {
            await run();
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {busy ? "Working…" : children}
      </button>
      {error && <Notice tone="error">{error}</Notice>}
    </>
  );
}
/** Complete inert fallback for server-defined fields, without narrowing recursive columns. */
export function Details({ data }: { data: Row }) {
  if (data === null || typeof data !== "object" || Array.isArray(data))
    return <DetailValue value={data} />;
  if (!Object.keys(data).length)
    return <p className="muted">No fields reported (empty object)</p>;
  return (
    <dl className="details">
      {Object.entries(data).map(([key, value]) => (
        <div
          key={key}
          className={
            value !== null && typeof value === "object"
              ? "detail-group"
              : undefined
          }
        >
          <dt title={key}>{label(key)}</dt>
          <dd>
            <DetailValue value={value} />
          </dd>
        </div>
      ))}
    </dl>
  );
}
function DetailValue({ value }: { value: unknown }) {
  if (value === null) return <>Not reported</>;
  if (value === undefined) return <>Unavailable</>;
  if (value === "") return <>Empty text</>;
  if (Array.isArray(value))
    return value.length ? (
      <ul className="detail-items">
        {value.map((item, index) => (
          <li key={index}>
            <DetailValue value={item} />
          </li>
        ))}
      </ul>
    ) : (
      <>No items reported (empty list)</>
    );
  if (typeof value === "object") return <Details data={value as Row} />;
  if (typeof value === "boolean") return <>{value ? "Yes" : "No"}</>;
  return <>{String(value)}</>;
}

/** Print all source/technical disclosures, then restore the reader's screen state. */
export function PrintSupport() {
  useEffect(() => {
    let closed: HTMLDetailsElement[] = [];
    let printing = false;
    const before = () => {
      if (printing) return;
      printing = true;
      closed = Array.from(
        document.querySelectorAll<HTMLDetailsElement>(
          "main details:not([open])",
        ),
      );
      closed.forEach((detail) => {
        detail.open = true;
      });
    };
    const after = () => {
      closed.forEach((detail) => {
        detail.open = false;
      });
      closed = [];
      printing = false;
    };
    window.addEventListener("beforeprint", before);
    window.addEventListener("afterprint", after);
    return () => {
      window.removeEventListener("beforeprint", before);
      window.removeEventListener("afterprint", after);
    };
  }, []);
  return null;
}

export function Icon({ name }: { name: string }) {
  const paths: Record<string, ReactNode> = {
    organizations: (
      <>
        <path d="M3 20V8l9-5 9 5v12M7 20v-7h10v7M7 8h.01M12 8h.01M17 8h.01" />
      </>
    ),
    overview: (
      <>
        <rect x="3" y="3" width="7" height="7" rx="1" />
        <rect x="14" y="3" width="7" height="7" rx="1" />
        <rect x="3" y="14" width="7" height="7" rx="1" />
        <rect x="14" y="14" width="7" height="7" rx="1" />
      </>
    ),
    programs: (
      <>
        <rect x="3" y="5" width="18" height="15" rx="2" />
        <path d="M3 10h18M8 5V3M16 5V3" />
      </>
    ),
    plans: (
      <>
        <path d="M7 3h14v16H7zM3 7v14h14M11 8h6M11 12h6" />
      </>
    ),
    plan: (
      <>
        <path d="M4 20 20 4M10 4h10v10M4 9v11h11" />
      </>
    ),
    upload: (
      <>
        <path d="M12 16V3m-5 5 5-5 5 5M4 16v5h16v-5" />
      </>
    ),
    report: (
      <>
        <path d="M5 3h10l4 4v14H5zM14 3v5h5M9 12h6M9 16h6" />
      </>
    ),
    evidence: (
      <>
        <path d="M3 4h7l2 2 2-2h7v15h-7l-2 2-2-2H3zM12 6v15" />
      </>
    ),
    saved: <path d="M6 3h12v18l-6-4-6 4z" />,
    analysis: (
      <>
        <path d="M3 3v18h18M8 16V9M13 16V5M18 16v-4" />
      </>
    ),
    connections: (
      <>
        <circle cx="5" cy="5" r="3" />
        <circle cx="19" cy="12" r="3" />
        <circle cx="5" cy="19" r="3" />
        <path d="m8 6 8 5M8 18l8-5" />
      </>
    ),
    watch: (
      <>
        <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" />
        <circle cx="12" cy="12" r="3" />
      </>
    ),
    alerts: (
      <>
        <path d="M6 9a6 6 0 0 1 12 0v6l2 3H4l2-3zM10 21h4" />
      </>
    ),
    review: (
      <>
        <path d="M9 3H5v18h14V3h-4M9 2h6v4H9zM8 13l3 3 5-6" />
      </>
    ),
    privacy: (
      <>
        <path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6zM9 12l2 2 4-4" />
      </>
    ),
    settings: (
      <>
        <path d="M4 6h16M4 12h16M4 18h16" />
        <circle cx="9" cy="6" r="2" />
        <circle cx="16" cy="12" r="2" />
        <circle cx="8" cy="18" r="2" />
      </>
    ),
    info: (
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 11v6M12 7h.01" />
      </>
    ),
    menu: <path d="M3 6h18M3 12h18M3 18h18" />,
    close: <path d="m6 6 12 12M6 18 18 6" />,
  };
  return (
    <svg
      className="icon"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {paths[name] || paths.report}
    </svg>
  );
}
export function Sources({ sources }: { sources: Row[] }) {
  return (
    <details className="source-drawer">
      <summary>Sources & provenance ({sources.length})</summary>
      {sources.map((s) => (
        <div className="source" key={s.id}>
          <h3>
            <Link href={`/sources/${s.id}`}>{s.title}</Link>
          </h3>
          <Badge>{s.kind}</Badge>
          <p>
            Reporting period {date(s.period_start)} – {date(s.period_end)} ·
            Retrieved {date(s.retrieved_at)}
          </p>
          <p>
            Revision {s.revision} · {s.parser_version} ·{" "}
            {s.locator || "Locator not supplied"}
          </p>
          {s.source_url && /^https?:\/\//.test(s.source_url) && (
            <a href={s.source_url} target="_blank" rel="noreferrer">
              Open original source ↗
            </a>
          )}
          <small className="checksum">Checksum {s.checksum}</small>
        </div>
      ))}
    </details>
  );
}
export function ReviewSubmit({
  artifact,
  onSaved,
}: {
  artifact: Row;
  onSaved: () => void;
}) {
  const { data } = useResource<Row[]>("reviewers/");
  return (
    <details className="source-drawer">
      <summary>Submit revision {artifact.revision} for review</summary>
      <p>A separate reviewer must approve the current source snapshot.</p>
      <Form
        submit="Submit for review"
        onSubmit={async (f) => {
          await mutate(`artifacts/${artifact.id}/submit/`, "POST", {
            revision: artifact.revision,
            reviewer_id: Number(f.get("reviewer_id")),
          });
          onSaved();
        }}
      >
        <Field label="Assigned reviewer" name="reviewer_id">
          <select name="reviewer_id" required>
            <option value="">Select reviewer</option>
            {data?.map((r) => (
              <option value={r.id} key={r.id}>
                {r.username}
              </option>
            ))}
          </select>
        </Field>
      </Form>
    </details>
  );
}
export function ExportButton({ id }: { id: string }) {
  return (
    <Action
      run={() => download(`reports/${id}/?format=csv`, "banyan-report.csv")}
    >
      Export CSV ↓
    </Action>
  );
}
export const text = (f: FormData, key: string) => String(f.get(key) || "");
