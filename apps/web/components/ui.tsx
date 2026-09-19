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
      <span className="empty-icon">◇</span>
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
        <p className="eyebrow">{eyebrow || "Philanthra workspace"}</p>
        <h1>{title}</h1>
        {children && <p className="lede">{children}</p>}
      </div>
      {action}
    </header>
  );
}
export function Panel({
  title,
  children,
  aside,
}: {
  title?: string;
  children: ReactNode;
  aside?: ReactNode;
}) {
  return (
    <section className="panel">
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
export function Details({ data }: { data: Row }) {
  return (
    <dl className="details">
      {Object.entries(data).map(([key, value]) => (
        <div key={key}>
          <dt>{label(key)}</dt>
          <dd>
            {value === null || value === undefined || value === "" ? (
              "Not reported"
            ) : Array.isArray(value) ? (
              value.length ? (
                value.map((v, i) => (
                  <div key={i}>
                    {typeof v === "object" ? <Details data={v} /> : String(v)}
                  </div>
                ))
              ) : (
                "None reported"
              )
            ) : typeof value === "object" ? (
              <Details data={value} />
            ) : typeof value === "boolean" ? (
              value ? (
                "Yes"
              ) : (
                "No"
              )
            ) : (
              String(value)
            )}
          </dd>
        </div>
      ))}
    </dl>
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
      run={() => download(`reports/${id}/?format=csv`, "philanthra-report.csv")}
    >
      Export CSV ↓
    </Action>
  );
}
export const text = (f: FormData, key: string) => String(f.get(key) || "");
