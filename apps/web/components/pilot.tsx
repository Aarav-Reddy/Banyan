"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Row, api, mutate, download, date, label } from "@/lib/api";
import { useWorkspace } from "./application";
import { ImpactReportContent, TechnicalDetails } from "./report-content";
import {
  Header,
  Panel,
  State,
  Empty,
  Notice,
  Badge,
  Field,
  Textarea,
  Form,
  Details,
  Sources,
  ReviewSubmit,
  Action,
  useResource,
  text,
} from "./ui";

export function Attributions({ artifact }: { artifact: Row }) {
  if (!artifact.attributions?.length) return null;
  return (
    <div className="attributions">
      <strong>Required source attribution</strong>
      <ul>
        {artifact.attributions.map((a: Row, i: number) => (
          <li key={`${a.source_id}-${i}`}>
            {a.text} <Link href={`/sources/${a.source_id}`}>Source record</Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function CreateWorkspace() {
  return (
    <Panel title="Create an independent workspace" variant="open">
      <p>
        Existing invited accounts can create a private NGO or foundation
        workspace. An NGO identity remains unlinked until an independent
        reviewer verifies your claim.
      </p>
      <Form
        submit="Create workspace"
        onSubmit={async (form) => {
          const created = await mutate("pilot/workspaces/", "POST", {
            name: text(form, "workspace_name"),
            kind: text(form, "workspace_kind"),
          });
          window.dispatchEvent(
            new CustomEvent("philanthra:workspace-created", {
              detail: created.id,
            }),
          );
        }}
      >
        <Field label="New workspace name" name="workspace_name" required />
        <Field label="New workspace type" name="workspace_kind">
          <select name="workspace_kind">
            <option value="ngo">NGO contributor</option>
            <option value="foundation">Foundation</option>
          </select>
        </Field>
      </Form>
    </Panel>
  );
}

export function PasswordReset() {
  const query = useSearchParams();
  const uid = query.get("uid"),
    token = query.get("token");
  const confirm = Boolean(uid && token);
  const [result, setResult] = useState<Row | null>(null);
  return (
    <main className="public-content auth-page">
      <Header title={confirm ? "Choose a new password" : "Reset your password"}>
        Reset instructions use the email address on your account.
      </Header>
      <Panel title={confirm ? "Reset password" : "Request reset instructions"}>
        {result ? (
          <Notice tone="success">
            {result.message} <Link href="/login">Return to sign in</Link>
          </Notice>
        ) : (
          <Form
            submit={confirm ? "Update password" : "Request reset email"}
            onSubmit={async (f) => {
              if (confirm && text(f, "password") !== text(f, "confirmation"))
                throw new Error("The passwords do not match.");
              setResult(
                await mutate(
                  `pilot/password-reset/${confirm ? "confirm" : "request"}/`,
                  "POST",
                  confirm
                    ? { uid, token, password: text(f, "password") }
                    : { email: text(f, "email") },
                ),
              );
            }}
          >
            {confirm ? (
              <>
                <Field
                  label="New password"
                  name="password"
                  type="password"
                  autoComplete="new-password"
                  required
                />
                <Field
                  label="Confirm new password"
                  name="confirmation"
                  type="password"
                  autoComplete="new-password"
                  required
                />
              </>
            ) : (
              <Field
                label="Account email"
                name="email"
                type="email"
                autoComplete="email"
                required
              />
            )}
          </Form>
        )}
        <p className="fine">
          If mail is unavailable, contact your workspace administrator. Local
          demo delivery is stored on the local server for its operator.
        </p>
      </Panel>
    </main>
  );
}

export function WorkspaceProfile() {
  const ws = useWorkspace();
  const [version, setVersion] = useState(0);
  const { data, error } = useResource("pilot/profile/", version);
  const { data: areas } = useResource<Row[]>("geographies/");
  const canEdit = ["owner", "administrator"].includes(ws.role);
  return (
    <Panel title="Mission & service context" variant="open">
      <State data={data} error={error}>
        {data && (
          <>
            {canEdit ? (
              <Form
                submit="Save workspace profile"
                onSubmit={async (f) => {
                  let context;
                  try {
                    context = JSON.parse(text(f, "context"));
                  } catch {
                    throw new Error("Context must be a valid JSON object.");
                  }
                  if (
                    !context ||
                    Array.isArray(context) ||
                    typeof context !== "object"
                  )
                    throw new Error("Context must be an object.");
                  await mutate("pilot/profile/", "PATCH", {
                    revision: data.revision,
                    mission: text(f, "mission"),
                    cause: text(f, "cause"),
                    population: text(f, "population"),
                    service_area_codes: f.getAll("service_area_codes"),
                    context,
                  });
                  setVersion(version + 1);
                }}
              >
                <Textarea label="Mission" name="mission" value={data.mission} />
                <div className="form-grid">
                  <Field
                    label="Primary cause"
                    name="cause"
                    value={data.cause}
                  />
                  <Field
                    label="Population served"
                    name="population"
                    value={data.population}
                  />
                </div>
                <fieldset>
                  <legend>Owner-reported service areas</legend>
                  {areas?.map((g) => (
                    <label className="check-label" key={g.code}>
                      <input
                        type="checkbox"
                        name="service_area_codes"
                        value={g.code}
                        defaultChecked={data.service_area_codes.includes(
                          g.code,
                        )}
                      />
                      {g.name} ({g.kind})
                    </label>
                  ))}
                </fieldset>
                <details>
                  <summary>
                    <span>Additional structured context</span> ·{" "}
                    {Object.keys(data.context).length} fields saved
                  </summary>
                  <Textarea
                    label="Context JSON"
                    name="context"
                    value={JSON.stringify(data.context, null, 2)}
                  />
                </details>
                <p className="fine">
                  {data.visibility}. Revision {data.revision}.
                </p>
              </Form>
            ) : (
              <Details data={data} />
            )}
          </>
        )}
      </State>
    </Panel>
  );
}

export function IdentityClaims() {
  const ws = useWorkspace();
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("pilot/identity-claims/", version);
  const { data: sources } = useResource<Row[]>("sources/");
  const { data: organizations } = useResource<Row[]>("organizations/");
  const canEdit = ["owner", "administrator"].includes(ws.role);
  if (ws.kind !== "ngo") return null;
  return (
    <Panel title="Organization identity" variant="open">
      <p>
        Public identity linkage requires independent review of your authority to
        represent the organization.
      </p>
      {ws.organization_id ? (
        <Notice>
          Linked organization:{" "}
          <Link href={`/organizations/${ws.organization_id}`}>
            Inspect public profile
          </Link>
          . Withdrawal of identity proof revokes the link.
        </Notice>
      ) : (
        canEdit && (
          <Form
            submit="Create identity claim"
            onSubmit={async (f) => {
              await mutate("pilot/identity-claims/", "POST", {
                organization_id: text(f, "organization_id"),
                proof_source_id: text(f, "proof_source_id"),
                statement: text(f, "statement"),
              });
              setVersion(version + 1);
            }}
          >
            <Field label="Organization to represent" name="organization_id">
              <select name="organization_id" required>
                <option value="">Choose an organization</option>
                {organizations?.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Owned proof source" name="proof_source_id">
              <select name="proof_source_id" required>
                <option value="">Choose uploaded proof</option>
                {sources
                  ?.filter((s) => s.owner_id === ws.id && s.state === "active")
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
              </select>
            </Field>
            <p className="fine">
              <Link href="/uploads">Upload a proof document</Link> first. Its
              source locator must permit reviewer inspection.
            </p>
            <Textarea
              label="Authority statement and proof locator"
              name="statement"
              required
            />
          </Form>
        )
      )}
      <State data={data} error={error}>
        {data?.map((c) => (
          <div className="source" key={c.id}>
            <h3>{c.organization.name}</h3>
            <Badge>{c.status}</Badge>
            <p>{c.statement}</p>
            {canEdit && c.status !== "approved" && (
              <ReviewSubmit
                artifact={{ id: c.artifact_id, revision: c.revision }}
                onSaved={() => setVersion(version + 1)}
              />
            )}
          </div>
        ))}
        {data?.length === 0 && (
          <p className="fine">No identity claims submitted.</p>
        )}
      </State>
    </Panel>
  );
}

export function IdentityProof({ id }: { id: string }) {
  const { data, error } = useResource(`pilot/identity-claims/${id}/proof/`);
  return (
    <State data={data} error={error}>
      {data && (
        <div className="source">
          <h3>Scoped identity evidence</h3>
          <Notice>{data.limitation}</Notice>
          <p>{data.statement}</p>
          <Badge>{data.validation_status}</Badge>
          {data.document_preview.length ? (
            <Details data={{ document_preview: data.document_preview }} />
          ) : (
            <p>
              No quarantined document preview is available; inspect the source
              locator and verify authority independently.
            </p>
          )}
          <Sources sources={[data.source]} />
        </div>
      )}
    </State>
  );
}

export function ContactConsent() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource("pilot/contact/", version);
  return (
    <Panel title="Optional contact sharing" variant="open">
      <State data={data} error={error}>
        {data && (
          <Form
            submit="Save contact consent"
            onSubmit={async (f) => {
              await mutate("pilot/contact/", "PUT", {
                revision: data.revision,
                name: text(f, "name"),
                email: text(f, "email"),
                enabled: f.has("enabled"),
              });
              setVersion(version + 1);
            }}
          >
            <div className="form-grid">
              <Field
                label="Contact name"
                name="name"
                value={data.name}
                required
              />
              <Field
                label="Contact email"
                name="email"
                type="email"
                value={data.email}
                required
              />
            </div>
            <label className="check-label">
              <input
                type="checkbox"
                name="enabled"
                defaultChecked={data.enabled}
              />
              Permit this contact to be shown to workspaces whose introduction
              requests we accept.
            </label>
            <p className="fine">
              Disabled by default. You can turn off sharing at any time;
              existing downloaded details cannot be recalled. No message is
              sent.
            </p>
          </Form>
        )}
      </State>
    </Panel>
  );
}

export function IntroductionInbox() {
  const ws = useWorkspace();
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("pilot/introductions/", version);
  return (
    <Panel title="Incoming introduction requests" variant="open">
      <State data={data} error={error}>
        {data?.map((r) => (
          <div className="source" key={r.id}>
            <h3>{r.from_workspace}</h3>
            <p>{r.note}</p>
            <Badge>{r.state}</Badge>
            {["owner", "administrator"].includes(ws.role) && (
              <Form
                submit="Save introduction decision"
                onSubmit={async (f) => {
                  await mutate(
                    `pilot/introductions/${r.id}/decision/`,
                    "POST",
                    { state: text(f, "state") },
                  );
                  setVersion(version + 1);
                }}
              >
                <Field label={`Decision for ${r.from_workspace}`} name="state">
                  <select
                    name="state"
                    defaultValue={
                      r.state === "accepted" ? "accepted" : "declined"
                    }
                  >
                    <option value="declined">Decline</option>
                    <option value="accepted">Accept</option>
                  </select>
                </Field>
                <p className="fine">
                  Acceptance reveals contact only when optional contact sharing
                  is enabled. No outbound message is sent.
                </p>
              </Form>
            )}
          </div>
        ))}
        {data?.length === 0 && (
          <Empty title="No incoming introduction requests" />
        )}
      </State>
    </Panel>
  );
}

export function PermittedContact({ id }: { id: string }) {
  const [contact, setContact] = useState<Row | null>(null);
  return (
    <div>
      <Action
        run={async () =>
          setContact(await api(`pilot/introductions/${id}/contact/`))
        }
      >
        View permitted contact
      </Action>
      {contact && <Details data={contact} />}
    </div>
  );
}

export function SaveEvidence({ id }: { id: string }) {
  const ws = useWorkspace();
  const [saved, setSaved] = useState(false);
  if (["viewer", "reviewer"].includes(ws.role)) return null;
  return (
    <div className="no-print">
      <Action
        run={async () => {
          await mutate("pilot/bookmarks/", "POST", { artifact_id: id });
          setSaved(true);
        }}
      >
        {saved ? "Evidence saved" : "Save evidence"}
      </Action>
      {saved && (
        <Link className="inline-link" href="/saved">
          Open saved evidence →
        </Link>
      )}
    </div>
  );
}

export function SavedEvidence() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("pilot/bookmarks/", version);
  const ws = useWorkspace();
  return (
    <>
      <Header title="Saved evidence">
        Saved for your workspace. Revoked evidence disappears immediately.
      </Header>
      <State data={data} error={error}>
        {data?.map((b) => (
          <Panel key={b.id} title={b.artifact.title} variant="open">
            <p>{b.artifact.payload.summary}</p>
            <Badge>{b.artifact.status}</Badge>
            <Attributions artifact={b.artifact} />
            <div className="actions">
              <Link href={`/evidence/${b.artifact.id}`}>
                Inspect evidence →
              </Link>
              {!["viewer", "reviewer"].includes(ws.role) && (
                <Action
                  run={async () => {
                    await mutate(`pilot/bookmarks/${b.id}/`, "DELETE");
                    setVersion(version + 1);
                  }}
                >
                  Remove saved evidence
                </Action>
              )}
            </div>
          </Panel>
        ))}
        {data?.length === 0 && (
          <Empty title="No saved evidence yet">
            <Link href="/evidence">Explore the evidence library</Link> and save
            a card for later.
          </Empty>
        )}
      </State>
    </>
  );
}

export function WatchOrganization({ id }: { id: string }) {
  const ws = useWorkspace();
  const [saved, setSaved] = useState(false);
  if (["viewer", "reviewer"].includes(ws.role)) return null;
  return (
    <>
      <Action
        run={async () => {
          await mutate("pilot/watchlist/", "POST", { organization_id: id });
          setSaved(true);
        }}
      >
        {saved ? "Organization watched" : "Watch organization"}
      </Action>
      {saved && <Link href="/watchlist">Open watchlist →</Link>}
    </>
  );
}

export function Watchlist() {
  const [version, setVersion] = useState(0),
    [job, setJob] = useState<Row | null>(null);
  const { data, error } = useResource<Row[]>("pilot/watchlist/", version);
  const ws = useWorkspace(),
    canEdit = !["viewer", "reviewer"].includes(ws.role);
  return (
    <>
      <Header
        title="Watchlist"
        action={
          <button
            type="button"
            className="secondary"
            onClick={() => setVersion(version + 1)}
          >
            Refresh watchlist
          </button>
        }
      >
        Monitor stored filing, funding and permitted evidence revisions. New
        alerts reflect changes since the stored snapshot.
      </Header>
      <Panel title="Monitoring">
        <div className="actions">
          {canEdit && (
            <Action
              run={async () => setJob(await mutate("pilot/monitor/", "POST"))}
            >
              Run monitoring check
            </Action>
          )}
          <Link href="/jobs">Inspect background jobs</Link>
          <Link href="/alerts">Open alerts</Link>
        </div>
        {job && (
          <Notice>
            Monitoring job {job.job_id}: {label(job.state)}. The worker
            processes it asynchronously; refresh after completion.
          </Notice>
        )}
      </Panel>
      <State data={data} error={error}>
        <Panel title="Watched organizations" variant="open">
          {data?.map((w) => (
            <div className="list-row" key={w.id}>
              <div>
                <Link href={`/organizations/${w.organization_id}`}>
                  {w.organization_name}
                </Link>
                <p>
                  Snapshot updated {date(w.last_checked_at)} ·{" "}
                  {label(w.monitor_status)}
                </p>
              </div>
              {canEdit && (
                <Action
                  run={async () => {
                    await mutate(`pilot/watchlist/${w.id}/`, "DELETE");
                    setVersion(version + 1);
                  }}
                >
                  Remove watch
                </Action>
              )}
            </div>
          ))}
          {data?.length === 0 && (
            <Empty title="Your watchlist is empty">
              Open an <Link href="/discover">organization profile</Link> to
              start watching its source records.
            </Empty>
          )}
        </Panel>
      </State>
    </>
  );
}

export function Benchmark() {
  const { data, error } = useResource("pilot/benchmark/");
  return (
    <Panel title="Compatible financial peers" variant="open">
      <State data={data} error={error}>
        {data && (
          <>
            <Badge>{data.status}</Badge>
            {data.reason && <Notice>{data.reason}</Notice>}
            {data.status === "available" && (
              <>
                <Details
                  data={{
                    peer_organizations: data.peer_organization_count,
                    program_spending_share_ratio: data.target_value,
                    peer_median_ratio: data.median,
                    peer_minimum_ratio: data.minimum,
                    peer_maximum_ratio: data.maximum,
                    difference_from_median: data.difference_from_median,
                    compatible_dimensions: data.dimensions,
                  }}
                />
                <details>
                  <summary>Method and source records</summary>
                  <p>{data.method_version}</p>
                  <ul>
                    {data.source_ids.map((id: string) => (
                      <li key={id}>
                        <Link href={`/sources/${id}`}>Source {id}</Link>
                      </li>
                    ))}
                  </ul>
                  <Details data={{ exclusions: data.excluded }} />
                </details>
              </>
            )}
            {data.limitations?.map((s: string) => (
              <p className="fine" key={s}>
                {s}
              </p>
            ))}
          </>
        )}
      </State>
    </Panel>
  );
}

export function ImpactReport() {
  const { data, error } = useResource("pilot/impact-report/");
  return (
    <State data={data} error={error}>
      {data && (
        <article className="report-document">
          <Header
            eyebrow="Private contributor report / Draft"
            title={`${data.workspace.name}: program evidence`}
            action={
              <div className="actions no-print">
                <button
                  type="button"
                  className="primary"
                  onClick={() => window.print()}
                >
                  Print impact report
                </button>
                <Action
                  run={() =>
                    download(
                      "pilot/impact-report/?format=csv",
                      "philanthra-impact-report-draft.csv",
                    )
                  }
                >
                  Export impact CSV ↓
                </Action>
              </div>
            }
          >
            Generated {date(data.generated_at)} · <Badge>{data.status}</Badge> ·{" "}
            <Badge>{data.source_kind}</Badge>
          </Header>
          <Notice>{data.limitations.join(" ")}</Notice>
          <ImpactReportContent
            data={data}
            attribution={(record) => <Attributions artifact={record} />}
          />
          <Attributions artifact={data} />
          <Sources sources={data.sources} />
          <TechnicalDetails data={data} />
        </article>
      )}
    </State>
  );
}

export function CommunityContext({ geographies }: { geographies: Row[] }) {
  const publicRows = geographies.filter(
    (g) =>
      g.context?.source_kind === "public_source" &&
      Array.isArray(g.context?.indicators),
  );
  return (
    <>
      {publicRows.map((g) => (
        <section className="community-context" key={g.code}>
          <h3>{g.context.geography_name}</h3>
          <Badge>Public source</Badge>
          <p className="fine">
            {date(g.context.period_start)} – {date(g.context.period_end)}
          </p>
          <dl>
            {g.context.indicators.map((i: Row) => (
              <div key={i.label}>
                <dt>{i.label}</dt>
                <dd>
                  {i.estimate == null
                    ? "Not reported"
                    : `${i.estimate} ${i.unit}`}
                </dd>
              </div>
            ))}
          </dl>
          <p className="fine">{g.context.caveat}</p>
          {/^https?:\/\//.test(g.context.source_url) && (
            <a href={g.context.source_url} target="_blank" rel="noreferrer">
              Census source table ↗
            </a>
          )}
          <p className="fine">Retrieved {date(g.context.retrieved_at)}</p>
        </section>
      ))}
    </>
  );
}

export function SourceIssues({ sourceId }: { sourceId?: string }) {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("source-issues/", version);
  const { data: sources } = useResource<Row[]>("sources/");
  const ws = useWorkspace(),
    canEdit = !["viewer", "reviewer"].includes(ws.role);
  return (
    <Panel title="Source corrections & disputes" variant="open">
      <p>
        Record a source-linked concern for independent review. A reviewed issue
        does not silently rewrite the underlying source.
      </p>
      {canEdit && (
        <Form
          submit="Create source issue"
          onSubmit={async (f) => {
            await mutate("source-issues/", "POST", {
              source_id: text(f, "source_id"),
              title: text(f, "title"),
              issue: text(f, "issue"),
            });
            setVersion(version + 1);
          }}
        >
          <Field label="Source to review" name="source_id">
            <select name="source_id" defaultValue={sourceId || ""} required>
              <option value="">Choose a source</option>
              {sources
                ?.filter((s) => s.state === "active")
                .map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.title}
                  </option>
                ))}
            </select>
          </Field>
          <Field label="Issue title" name="title" required />
          <Textarea
            label="Concern, supporting evidence and requested correction"
            name="issue"
            required
          />
        </Form>
      )}
      <State data={data} error={error}>
        {data
          ?.filter(
            (a) => !sourceId || a.sources.some((s: Row) => s.id === sourceId),
          )
          .map((a) => (
            <div className="source" key={a.id}>
              <h3>{a.title}</h3>
              <Badge>{a.status}</Badge>
              <Details data={a.payload} />
              <Attributions artifact={a} />
              {a.owner_id === ws.id && canEdit && (
                <ReviewSubmit
                  artifact={a}
                  onSaved={() => setVersion(version + 1)}
                />
              )}
            </div>
          ))}
        {data?.length === 0 && (
          <p className="fine">No source issues recorded in this workspace.</p>
        )}
      </State>
    </Panel>
  );
}
