"use client";
import Link from "next/link";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import { Row, label, date, money, mutate, download } from "@/lib/api";
import {
  useResource,
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
  ExportButton,
  Action,
  text,
} from "./ui";
import { useWorkspace } from "./application";
export function Analyses() {
  const [version, setVersion] = useState(0),
    [result, setResult] = useState<Row | null>(null);
  const { data, error } = useResource<Row[]>("analyses/", version);
  const { data: candidates } = useResource<Row[]>(
    "analyses/candidates/",
    version,
  );
  const ws = useWorkspace();
  const groups = new Map<string, Row[]>();
  for (const c of candidates || []) {
    const key = [c.outcome_definition, c.period_start, c.period_end].join(
      " · ",
    );
    groups.set(key, [...(groups.get(key) || []), c]);
  }
  return (
    <>
      <Header
        eyebrow="Shared intelligence / Fixed cohort releases"
        title="Find the pattern. Keep the context."
      >
        Combine compatible aggregate observations from consenting organizations.
        Descriptive pooling does not establish causality.
      </Header>
      <div className="two-columns">
        <Panel title="Create a fixed analysis">
          <Form
            submit="Calculate pooled draft"
            onSubmit={async (f) => {
              const rows = groups.get(text(f, "group"));
              if (!rows)
                throw new Error("Choose an available complete cohort set.");
              setResult(
                await mutate("analyses/", "POST", {
                  title: text(f, "title"),
                  observation_ids: rows.map((r) => r.id),
                  cause: text(f, "cause"),
                  geography: text(f, "geography"),
                }),
              );
              setVersion(version + 1);
            }}
          >
            <Field
              label="Analysis title"
              name="title"
              value="Food security outcomes · fixed cohort review"
              required
            />
            <Field label="Complete outcome & period set" name="group">
              <select required name="group">
                <option value="">Select a fixed set</option>
                {[...groups].map(([key]) => (
                  <option value={key} key={key}>
                    {key}
                  </option>
                ))}
              </select>
            </Field>
            <div className="form-grid">
              <Field
                label="Cause"
                name="cause"
                value="food_security"
                required
              />
              <Field
                label="Geography"
                name="geography"
                value="US-MD-Baltimore"
                required
              />
            </div>
          </Form>
          {!groups.size && <Empty title="No authorized cohort sets" />}
        </Panel>
        <Panel title="Release safeguards">
          <ul className="checklist">
            <li>
              Compatible definitions, intervention, population, unit, and
              follow-up.
            </li>
            <li>
              Documented independent cohorts; duplicates cannot add evidence.
            </li>
            <li>
              At least 3 independent organizations and 10 participants in each
              disclosed binary cell and complement.
            </li>
            <li>
              Whole-release suppression. No arbitrary private-data slicing.
            </li>
            <li>Separate review bound to a specific source revision.</li>
          </ul>
          <p className="fine">
            Threshold suppression is not anonymization or differential privacy.
          </p>
        </Panel>
      </div>
      {result && (
        <Panel title="Latest calculation">
          <AnalysisResult payload={result.payload} />
        </Panel>
      )}
      <State data={data} error={error}>
        {data?.map((a) => (
          <Panel key={a.id} title={a.title} aside={<Badge>{a.status}</Badge>}>
            <AnalysisResult payload={a.payload} />
            <div className="actions">
              <Link className="button secondary" href={`/reports/${a.id}`}>
                Open analysis report
              </Link>
              <ExportButton id={a.id} />
            </div>
            {a.owner_id === ws.id && (
              <ReviewSubmit
                artifact={a}
                onSaved={() => setVersion(version + 1)}
              />
            )}
            <Sources sources={a.sources} />
          </Panel>
        ))}
        {data?.length === 0 && (
          <Empty title="No analysis releases yet">
            Create a fixed cohort draft, inspect compatibility, then submit for
            separate review.
          </Empty>
        )}
      </State>
    </>
  );
}
function AnalysisResult({ payload: p }: { payload: Row }) {
  if (["suppressed", "incompatible", "insufficient_data"].includes(p.status))
    return (
      <Notice tone="warning">
        <strong>{label(p.status)}.</strong> {p.reason}
      </Notice>
    );
  return (
    <>
      <div className="summary-strip">
        <div>
          <small>Sample-weighted descriptive rate</small>
          <strong>
            {p.weighted_rate != null
              ? `${(Number(p.weighted_rate) * 100).toFixed(1)}%`
              : "Unavailable"}
          </strong>
        </div>
        <div>
          <small>Equal-organization rate</small>
          <strong>
            {p.equal_organization_rate != null
              ? `${(Number(p.equal_organization_rate) * 100).toFixed(1)}%`
              : "Unavailable"}
          </strong>
        </div>
        <div>
          <small>Contributing organizations</small>
          <strong>{p.organization_count ?? "Unavailable"}</strong>
        </div>
      </div>
      {p.warnings?.map((w: string) => (
        <Notice tone="warning" key={w}>
          {w}
        </Notice>
      ))}
      {p.per_organization && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Organization</th>
                <th>Numerator</th>
                <th>Denominator</th>
                <th>Descriptive rate</th>
                <th>Studies</th>
              </tr>
            </thead>
            <tbody>
              {p.per_organization.map((o: Row) => (
                <tr key={o.organization_id}>
                  <td>
                    <Link href={`/organizations/${o.organization_id}`}>
                      Organization {o.organization_id.slice(0, 8)} ↗
                    </Link>
                  </td>
                  <td>{o.numerator}</td>
                  <td>{o.denominator}</td>
                  <td>{(Number(o.rate) * 100).toFixed(1)}%</td>
                  <td>{o.study_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p>{p.uncertainty}</p>
      <details className="source-drawer">
        <summary>Compatibility, coverage & limitations</summary>
        <Details
          data={{
            compatibility: p.compatibility,
            cohort_count: p.cohort_count,
            study_count: p.study_count,
            limitations: p.limitations,
            thresholds: p.thresholds,
          }}
        />
      </details>
    </>
  );
}
export function Graph() {
  const q = useSearchParams();
  const [root, setRoot] = useState(q.get("root") || ""),
    [selected, setSelected] = useState<Row | null>(null);
  const { data, error } = useResource(
    `graph/?root=${encodeURIComponent(root)}`,
  );
  const edges: Row[] = data?.edges || [];
  return (
    <>
      <Header title="Follow the evidence connections.">
        Explore actual, source-backed relationships. Access is checked before
        traversal.
      </Header>
      <Panel>
        <Form
          className="inline-form"
          submit="Explore record"
          onSubmit={async (f) => {
            setRoot(text(f, "root"));
            setSelected(null);
          }}
        >
          <Field
            label="Root record identifier (optional)"
            name="root"
            value={root}
          />
        </Form>
        <button
          className="text-button"
          onClick={() => {
            setRoot("");
            setSelected(null);
          }}
        >
          Show all permitted relationships
        </button>
      </Panel>
      <State data={data} error={error}>
        {edges.length ? (
          <>
            <Panel title="Relationship map">
              <div className="graph-visual">
                {edges.slice(0, 12).map((e) => (
                  <button
                    className={`graph-edge ${selected?.id === e.id ? "selected" : ""}`}
                    key={e.id}
                    onClick={() => setSelected(e)}
                  >
                    <span>
                      <small>{label(e.source_type)}</small>
                      {e.source_id.slice(0, 8)}
                    </span>
                    <em>{label(e.relation)} →</em>
                    <span>
                      <small>{label(e.target_type)}</small>
                      {e.target_id.length > 24
                        ? e.target_id.slice(0, 8)
                        : e.target_id}
                    </span>
                  </button>
                ))}
              </div>
              <p className="fine">
                First 12 relationships shown visually; full accessible edge
                table below. Query bound: {data?.limit} edges.
              </p>
            </Panel>
            {selected && (
              <Panel title="Relationship & provenance">
                <Details
                  data={{
                    relationship: selected.relation,
                    from: selected.source_type,
                    to: selected.target_type,
                  }}
                />
                <div className="actions">
                  <Link href={`/sources/${selected.supporting_source_id}`}>
                    Supporting source ↗
                  </Link>
                  <Link href={`/evidence/${selected.artifact_id}`}>
                    Evidence record ↗
                  </Link>
                  <button
                    onClick={() => setRoot(selected.target_id)}
                    className="secondary"
                  >
                    Explore connected node
                  </button>
                </div>
              </Panel>
            )}
            <Panel title="Accessible relationship table">
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>From</th>
                      <th>Relationship</th>
                      <th>To</th>
                      <th>Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {edges.map((e) => (
                      <tr key={e.id}>
                        <td>
                          {label(e.source_type)}
                          <small>{e.source_id}</small>
                        </td>
                        <td>
                          <button
                            className="text-button"
                            onClick={() => setSelected(e)}
                          >
                            {label(e.relation)}
                          </button>
                        </td>
                        <td>
                          {label(e.target_type)}
                          <small>{e.target_id}</small>
                        </td>
                        <td>
                          <Link href={`/sources/${e.supporting_source_id}`}>
                            Inspect citation
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        ) : (
          <Empty title="No permitted connections">
            The record may have been withdrawn, or there may be no shared
            evidence for this workspace.
          </Empty>
        )}
      </State>
    </>
  );
}
export function Alerts() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("alerts/", version);
  const { data: subscriptions } = useResource("subscriptions/", version);
  return (
    <>
      <Header title="Changes worth your attention.">
        In-app updates tied to stored source revisions, evidence, and your
        program context.
      </Header>
      <details className="source-drawer">
        <summary>Alert subscription preferences</summary>
        {subscriptions && (
          <Form
            submit="Save subscriptions"
            onSubmit={async (f) => {
              await mutate(
                "subscriptions/",
                "PATCH",
                Object.fromEntries(
                  ["evidence", "financial", "stale"].map((k) => [k, f.has(k)]),
                ),
              );
              setVersion(version + 1);
            }}
          >
            {["evidence", "financial", "stale"].map((k) => (
              <label className="check-label" key={k}>
                <input
                  type="checkbox"
                  name={k}
                  defaultChecked={subscriptions[k]}
                />
                {label(k)} updates
              </label>
            ))}
            <p className="fine">
              Workspace owner or administrator permission is required.
            </p>
          </Form>
        )}
      </details>
      <State data={data} error={error}>
        {data?.map((a) => (
          <Panel key={a.id} title={a.title} aside={<Badge>{a.state}</Badge>}>
            <p>{a.explanation}</p>
            <p className="fine">Created {date(a.created_at)}</p>
            <Link href={`/reports/${a.artifact_id}`}>
              Inspect supporting artifact →
            </Link>
            <Form
              className="form"
              submit="Save alert response"
              onSubmit={async (f) => {
                await mutate(`alerts/${a.id}/`, "PATCH", {
                  state: text(f, "state"),
                  feedback: text(f, "feedback"),
                  adoption_note: text(f, "adoption_note"),
                });
                setVersion(version + 1);
              }}
            >
              <div className="form-grid">
                <Field label="Action" name="state">
                  <select
                    name="state"
                    defaultValue={a.state === "new" ? "read" : a.state}
                  >
                    {["read", "dismissed", "saved", "resolved", "adopted"].map(
                      (s) => (
                        <option key={s} value={s}>
                          {label(s)}
                        </option>
                      ),
                    )}
                  </select>
                </Field>
                <Field label="Relevance feedback" name="feedback">
                  <select name="feedback" defaultValue={a.feedback || ""}>
                    <option value="">Not yet rated</option>
                    <option value="useful">Useful</option>
                    <option value="not_useful">Not useful</option>
                    <option value="inaccurate">Inaccurate</option>
                  </select>
                </Field>
              </div>
              <Textarea
                name="adoption_note"
                label="Actual pilot adoption note (required for adopted)"
                value={a.adoption_note}
              />
            </Form>
          </Panel>
        ))}
        {data?.length === 0 && (
          <Empty title="You’re up to date">
            New eligible evidence and source changes create alerts after the
            worker processes them. Revoked insights are removed.
          </Empty>
        )}
      </State>
    </>
  );
}
export function Sharing() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("sources/", version);
  const { data: grants } = useResource<Row[]>("grants/", version);
  const ws = useWorkspace();
  const owned = data?.filter((s) => s.owner_id === ws.id) || [];
  const [chosen, setChosen] = useState("");
  const source = owned.find((s) => s.id === chosen);
  return (
    <>
      <Header
        title="Your evidence. Your permissions."
        action={
          <Link className="button secondary" href="/audit">
            Data-use activity ↗
          </Link>
        }
      >
        Private by default. Grant a specific purpose, recipient, geography, and
        cause. Withdraw access at any time.
      </Header>
      <Notice>
        Withdrawal immediately blocks new access to dependent records and queues
        physical deletion. Previously downloaded files cannot be recalled.
        Backups require operator-managed expiry.
      </Notice>
      <Panel title="Create a data-use grant">
        <Form
          submit="Grant scoped permission"
          onSubmit={async (f) => {
            if (!source) throw new Error("Choose an active owned source.");
            await mutate("grants/", "POST", {
              source_id: source.id,
              purpose: text(f, "purpose"),
              audience: text(f, "audience"),
              ...(text(f, "recipient_id")
                ? { recipient_id: text(f, "recipient_id") }
                : {}),
              cause: source.cause,
              geography: source.geography,
              attribution: text(f, "attribution"),
              ...(text(f, "expires_at")
                ? { expires_at: new Date(text(f, "expires_at")).toISOString() }
                : {}),
              external_processing: f.has("external_processing"),
            });
            setVersion(version + 1);
          }}
        >
          <div className="form-grid">
            <Field label="Owned source" name="source_id">
              <select
                name="source_id"
                required
                value={chosen}
                onChange={(e) => setChosen(e.target.value)}
              >
                <option value="">Choose a source</option>
                {owned
                  .filter((s) => s.state === "active")
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.title}
                    </option>
                  ))}
              </select>
            </Field>
            <Field label="Purpose" name="purpose">
              <select name="purpose">
                {[
                  "donor_access",
                  "benchmarking",
                  "pooled_analysis",
                  "publication",
                  "external_ai",
                ].map((p) => (
                  <option key={p} value={p}>
                    {label(p)}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Audience" name="audience">
              <select name="audience">
                <option value="workspace">Specific workspace</option>
                <option value="public">Public audience</option>
              </select>
            </Field>
            <Field
              label="Recipient workspace UUID"
              name="recipient_id"
              hint="Required for a specific workspace; blank for public audience."
            />
            <Field
              label="Expiry (optional)"
              name="expires_at"
              type="datetime-local"
            />
            <Field label="Required attribution" name="attribution" />
          </div>
          {source && (
            <p>
              Exact scope: {source.cause} · {source.geography}
            </p>
          )}
          <label className="check-label">
            <input type="checkbox" name="external_processing" /> I explicitly
            permit external model processing for an external AI grant.
          </label>
          <p className="fine">
            Owner or administrator permission is required. Publication still
            requires separate review.
          </p>
        </Form>
      </Panel>
      <Panel title="Current permissions">
        {grants?.map((g) => (
          <div className="list-row" key={g.id}>
            <div>
              <strong>
                {owned.find((s) => s.id === g.source)?.title || "Source record"}
              </strong>
              <p>
                {label(g.purpose)} · {g.audience} · {g.geography}
              </p>
              <small>
                Recipient {g.recipient || "Public audience"} · Expires{" "}
                {date(g.expires_at)}
              </small>
            </div>
            <Badge>{g.active ? "active" : "revoked"}</Badge>
            {g.active && (
              <Action
                danger
                run={async () => {
                  await mutate(`grants/${g.id}/`, "DELETE");
                  setVersion(version + 1);
                }}
              >
                Revoke grant
              </Action>
            )}
          </div>
        ))}
        {!grants?.length && <Empty title="No explicit sharing grants" />}
      </Panel>
      <Panel title="Owned sources & withdrawal">
        <State data={data} error={error}>
          {owned.map((s) => (
            <div className="source" key={s.id}>
              <div className="panel-heading">
                <Link href={`/sources/${s.id}`}>{s.title}</Link>
                <Badge>{s.state}</Badge>
              </div>
              {s.state === "active" && (
                <details>
                  <summary>Withdraw this source</summary>
                  <p>
                    This ends new access and invalidates dependent insights.
                    Type WITHDRAW to confirm the specific source.
                  </p>
                  <Form
                    submit="Withdraw source & queue deletion"
                    onSubmit={async (f) => {
                      if (text(f, "confirmation") !== "WITHDRAW")
                        throw new Error("Type WITHDRAW to confirm.");
                      await mutate(`sources/${s.id}/withdraw/`, "POST");
                      setVersion(version + 1);
                    }}
                  >
                    <Field
                      label={`Confirm withdrawal of ${s.title}`}
                      name="confirmation"
                      required
                    />
                  </Form>
                </details>
              )}
            </div>
          ))}
          {!owned.length && <Empty title="No owned source contributions" />}
        </State>
      </Panel>
    </>
  );
}
export function SourcesPage({ id }: { id?: string }) {
  const { data, error } = useResource<Row | Row[]>(
    id ? `sources/${id}/` : "sources/",
  );
  return (
    <>
      <Header
        title={id ? "Inspect the source." : "Every claim starts somewhere."}
      >
        Trace reporting periods, retrieval dates, source revisions, and
        transformations.
      </Header>
      <State data={data} error={error}>
        {data &&
          (id ? (
            <Panel title={(data as Row).title}>
              <Badge>{(data as Row).kind}</Badge>
              <Details data={data as Row} />
            </Panel>
          ) : (
            <Panel>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Source</th>
                      <th>Kind</th>
                      <th>Reporting period</th>
                      <th>Retrieved</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(data as Row[]).map((s) => (
                      <tr key={s.id}>
                        <td>
                          <Link href={`/sources/${s.id}`}>{s.title}</Link>
                          <small>
                            {s.parser_version} · revision {s.revision}
                          </small>
                        </td>
                        <td>
                          <Badge>{s.kind}</Badge>
                        </td>
                        <td>
                          {date(s.period_start)} – {date(s.period_end)}
                        </td>
                        <td>{date(s.retrieved_at)}</td>
                        <td>
                          <Badge>{s.state}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ))}
      </State>
    </>
  );
}
export function Settings() {
  const [version, setVersion] = useState(0),
    [invitation, setInvitation] = useState<Row | null>(null);
  const { data, error } = useResource<Row[]>("members/", version);
  const ws = useWorkspace();
  return (
    <>
      <Header title="Workspace settings.">
        {ws.name} · Your role: {label(ws.role)}
      </Header>
      <Panel title="Members & roles">
        <State data={data} error={error}>
          {data?.map((m) => (
            <div className="list-row" key={m.id}>
              <div>
                <strong>{m.username}</strong>
                <p>{label(m.role)}</p>
              </div>
              {["owner", "administrator"].includes(ws.role) &&
                m.role !== "owner" && (
                  <Form
                    className="inline-form"
                    submit="Update role"
                    onSubmit={async (f) => {
                      await mutate("members/", "PATCH", {
                        id: m.id,
                        role: text(f, "role"),
                      });
                      setVersion(version + 1);
                    }}
                  >
                    <Field name="role" label={`Role for ${m.username}`}>
                      <select name="role" defaultValue={m.role}>
                        {[
                          "administrator",
                          "analyst",
                          "editor",
                          "viewer",
                          "reviewer",
                        ].map((r) => (
                          <option key={r}>{r}</option>
                        ))}
                      </select>
                    </Field>
                  </Form>
                )}
            </div>
          ))}
        </State>
      </Panel>
      <div className="two-columns">
        <Panel title="Invite a collaborator">
          <Form
            submit="Create scoped invitation"
            onSubmit={async (f) =>
              setInvitation(
                await mutate("invitations/", "POST", {
                  email: text(f, "email"),
                  role: text(f, "role"),
                }),
              )
            }
          >
            <Field label="Email address" name="email" type="email" required />
            <Field label="Role" name="role">
              <select name="role">
                {["viewer", "analyst", "editor", "reviewer"].map((r) => (
                  <option key={r}>{r}</option>
                ))}
              </select>
            </Field>
          </Form>
          {invitation && (
            <Notice tone="success">
              <p>
                Invitation created. Share securely; no email was sent. Expires{" "}
                {date(invitation.expires_at)}.
              </p>
              <label className="field">
                <span>Single-use invitation token</span>
                <input readOnly value={invitation.token} />
              </label>
              <Link href="/join">Invitation redemption page</Link>
            </Notice>
          )}
        </Panel>
        <Panel title="Workspace boundaries">
          <Details
            data={{
              workspace_id: ws.id,
              kind: ws.kind,
              role: ws.role,
              organization_id: ws.organization_id,
            }}
          />
          <p>
            Membership is checked server-side for every request. An identifier
            alone grants no access.
          </p>
          <Link href="/metrics">Manage optional pilot measurement →</Link>
        </Panel>
      </div>
    </>
  );
}
export function Reviews() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("reviews/", version);
  return (
    <>
      <Header
        eyebrow="Assigned reviewer workbench"
        title="Review the evidence, not just the conclusion."
      >
        Decisions bind the exact revision and current source snapshot. You
        cannot approve your own work.
      </Header>
      <Notice>
        Demo approvals demonstrate the workflow; they are not real expert
        endorsements. Changed or withdrawn inputs invalidate approval.
      </Notice>
      <State data={data} error={error}>
        {data?.map((a) => (
          <Panel key={a.id} title={a.title} aside={<Badge>{a.kind}</Badge>}>
            <p>
              Revision {a.revision} · {a.cause} · {a.geography}
            </p>
            <Link
              href={
                a.kind === "card" ? `/evidence/${a.id}` : `/reports/${a.id}`
              }
            >
              Inspect complete artifact →
            </Link>
            <Sources sources={a.sources} />
            {a.kind === "analysis" && <AnalysisResult payload={a.payload} />}
            <Form
              submit="Record review decision"
              onSubmit={async (f) => {
                await mutate(`reviews/${a.id}/`, "POST", {
                  revision: a.revision,
                  decision: text(f, "decision"),
                  reason: text(f, "reason"),
                });
                setVersion(version + 1);
              }}
            >
              <Field label="Decision" name="decision">
                <select name="decision">
                  <option value="changes_requested">Request changes</option>
                  <option value="approved">Approve this revision</option>
                  <option value="rejected">Reject</option>
                  <option value="withdrawn">Withdraw</option>
                </select>
              </Field>
              <Textarea
                label="Reason, scope & caveats"
                name="reason"
                required
              />
            </Form>
          </Panel>
        ))}
        {data?.length === 0 && (
          <Empty title="No assigned reviews pending">
            Only explicit, current assignments grant scoped reviewer access.
            Ordinary administration does not expose private NGO records.
          </Empty>
        )}
      </State>
    </>
  );
}
export function Metrics() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource("metrics/", version);
  return (
    <>
      <Header title="Measure the pilot honestly.">
        Optional, workspace-scoped reporting. Actual funding and learning
        outcomes need human evidence.
      </Header>
      <State data={data} error={error}>
        {data && (
          <>
            <Notice>
              {data.warning} Ground truth: {data.ground_truth}.
            </Notice>
            <Panel title="Collection preferences">
              <Form
                submit="Save measurement preference"
                onSubmit={async (f) => {
                  await mutate("metrics/", "PATCH", {
                    opted_in: f.has("opted_in"),
                  });
                  setVersion(version + 1);
                }}
              >
                <label className="check-label">
                  <input
                    type="checkbox"
                    name="opted_in"
                    defaultChecked={data.opted_in}
                  />{" "}
                  Opt in to first-party pilot measurement
                </label>
                <p className="fine">
                  Workspace owner or administrator approval is required. No
                  third-party analytics.
                </p>
              </Form>
            </Panel>
            <Panel title="Record a measured pilot event">
              <Form
                submit="Save event"
                onSubmit={async (f) => {
                  await mutate("metrics/", "POST", {
                    metric: text(f, "metric"),
                    value: text(f, "value"),
                    denominator: text(f, "denominator") || null,
                    period_start: text(f, "period_start"),
                    period_end: text(f, "period_end"),
                    collection_method: text(f, "collection_method"),
                  });
                  setVersion(version + 1);
                }}
              >
                <Field label="Measure" name="metric">
                  <select name="metric">
                    {Object.keys(data.definitions).map((k) => (
                      <option key={k} value={k}>
                        {label(k)}
                      </option>
                    ))}
                  </select>
                </Field>
                <div className="form-grid">
                  <Field
                    label="Observed value"
                    name="value"
                    type="number"
                    step="any"
                    required
                  />
                  <Field
                    label="Denominator, if applicable"
                    name="denominator"
                    type="number"
                    step="any"
                  />
                  <Field
                    label="Period start"
                    name="period_start"
                    type="date"
                    required
                  />
                  <Field
                    label="Period end"
                    name="period_end"
                    type="date"
                    required
                  />
                </div>
                <Textarea
                  label="Collection method, baseline & ground truth"
                  name="collection_method"
                  required
                />
              </Form>
            </Panel>
            <Panel title="Measurement definitions">
              <Details data={data.definitions} />
            </Panel>
            <Panel title="Recorded events">
              {data.events.length ? (
                data.events.map((e: Row) => (
                  <div className="source" key={e.id}>
                    <h3>{label(e.metric)}</h3>
                    <Details data={e} />
                  </div>
                ))
              ) : (
                <Empty title="No ground-truth events collected">
                  Drafts and demo interactions are not pilot traction.
                </Empty>
              )}
            </Panel>
          </>
        )}
      </State>
    </>
  );
}
export function Jobs() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("jobs/", version);
  return (
    <>
      <Header
        title="Background work, made visible."
        action={
          <button className="secondary" onClick={() => setVersion(version + 1)}>
            Refresh jobs
          </button>
        }
      >
        Imports, matching, and deletion run through bounded retries and leases.
      </Header>
      <State data={data} error={error}>
        <Panel>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Job</th>
                  <th>State</th>
                  <th>Attempts</th>
                  <th>Last updated</th>
                  <th>Diagnostic</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((j) => (
                  <tr key={j.id}>
                    <td>
                      {label(j.kind)}
                      <small>{j.id}</small>
                    </td>
                    <td>
                      <Badge>{j.state}</Badge>
                    </td>
                    <td>
                      {j.attempts} / {j.max_attempts}
                    </td>
                    <td>{date(j.updated_at)}</td>
                    <td>{j.error_code || "No error reported"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data?.length === 0 && <Empty title="No jobs in this workspace" />}
        </Panel>
      </State>
    </>
  );
}
export function Report({ id }: { id: string }) {
  const { data, error } = useResource(`reports/${id}/`);
  return (
    <State data={data} error={error}>
      {data && (
        <>
          <Header
            eyebrow="Philanthra / Source-linked report"
            title={data.title}
            action={
              <div className="actions no-print">
                <button className="primary" onClick={() => window.print()}>
                  Print report
                </button>
                <ExportButton id={id} />
              </div>
            }
          >
            Revision {data.revision} · {date(data.created_at)} ·{" "}
            <Badge>{data.status}</Badge> · <Badge>{data.source_kind}</Badge>
          </Header>
          <Notice>
            This report is decision support. It does not move money, establish
            causal impact, or certify the underlying records. Missing
            information remains unknown.
          </Notice>
          {data.kind === "analysis" ? (
            <Panel title="Descriptive analysis">
              <AnalysisResult payload={data.payload} />
            </Panel>
          ) : data.kind === "portfolio" ? (
            <Panel title="Funding allocation">
              <Details
                data={{
                  budget: money(data.portfolio.budget_cents, true),
                  unallocated: money(data.portfolio.unallocated_cents, true),
                  method: data.method_version,
                }}
              />
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Organization</th>
                      <th>Amount</th>
                      <th>Reason</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.portfolio.allocations.map((a: Row) => (
                      <tr key={a.id}>
                        <td>{a.organization_name}</td>
                        <td>{money(a.amount_cents, true)}</td>
                        <td>{a.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          ) : (
            <Panel title="Evidence summary">
              <p>{data.payload.summary || "No summary reported."}</p>
              <Link href={`/evidence/${id}`}>
                Inspect full intervention card
              </Link>
            </Panel>
          )}
          <Panel title="Review & reproducibility">
            <Details
              data={{
                status: data.status,
                revision: data.revision,
                method_version: data.method_version,
                policy_version: data.policy_version,
                review: data.review || "Unreviewed",
              }}
            />
          </Panel>
          <Sources sources={data.sources} />
        </>
      )}
    </State>
  );
}
export function Audit() {
  const { data, error } = useResource<Row[]>("audit/");
  return (
    <>
      <Header title="Data-use activity.">
        Workspace-scoped records of imports, access changes, review, exports,
        and withdrawal. Application-enforced audit records are not advertised as
        tamper-proof.
      </Header>
      <State data={data} error={error}>
        <Panel>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Record</th>
                  <th>Timestamp</th>
                  <th>Operational metadata</th>
                </tr>
              </thead>
              <tbody>
                {data?.map((e) => (
                  <tr key={e.id}>
                    <td>{e.action}</td>
                    <td className="checksum">{e.object_id}</td>
                    <td>{e.created_at}</td>
                    <td>
                      <Details data={e.metadata} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data?.length === 0 && <Empty title="No recorded activity" />}
        </Panel>
      </State>
    </>
  );
}
export function Methodology() {
  return (
    <>
      <Header eyebrow="Methods & limitations" title="Clarity over certainty.">
        Philanthra helps people investigate and learn. Every calculation has
        boundaries; every consequential recommendation needs human review.
      </Header>
      <div className="two-columns">
        <Panel title="Financial warning signals">
          <p>
            Program-spending share is program expenses divided by positive total
            expenses. Operating margin is revenue minus expenses, divided by
            positive revenue. Liabilities/assets requires positive assets.
            Comparable consecutive periods are required for growth.
          </p>
          <p>
            Missing fields remain unknown. Net assets are not cash. Cash runway
            requires documented unrestricted cash and comparable annual
            expenses.
          </p>
          <Notice>
            Rules are investigation signals, not validated bankruptcy
            probabilities. Program-spending share is not impact.
          </Notice>
        </Panel>
        <Panel title="Funding allocations">
          <p>
            The pilot uses a deterministic, constrained proportional planning
            heuristic. Donor-selected weights, candidate exclusions, caps,
            minimums, and exact integer cents determine the result.
          </p>
          <p>
            Unknown capacity requires a disclosed planning assumption.
            Infeasible constraints leave funds unallocated. Drafts are versioned
            and require separate review; edits invalidate approval.
          </p>
          <p>No payments, grant submission, or pay-to-rank.</p>
        </Panel>
        <Panel title="Learning & transfer">
          <p>
            Cause, intervention, population, setting, duration, resources, and
            infrastructure inform deterministic matching. Similarities,
            differences, and missing fields stay visible.
          </p>
          <p>
            Country identity does not establish transferability. Editorial
            approval does not change study design. Failed and contradictory
            interventions remain part of the evidence.
          </p>
          <p>
            Optional model explanations cannot authoritatively compute money or
            invent claims and citations. The default provider is off.
          </p>
        </Panel>
        <Panel title="Pooling & privacy">
          <p>
            Only compatible definitions, units, populations, interventions,
            follow-up periods, and independently documented cohorts may be
            pooled. Sample-weighted and equal-organization summaries are
            descriptive.
          </p>
          <p>
            Fixed releases need at least three independent organizations and at
            least ten in every disclosed binary cell and complement. Suppressed
            releases disclose no reconstructable totals.
          </p>
          <p>
            These thresholds are policy choices, not a guarantee of anonymity.
            Heterogeneity and possible Simpson reversals must be inspected.
          </p>
        </Panel>
        <Panel title="Data provenance">
          <p>
            Public sources, NGO contributions, and synthetic demonstrations are
            distinguished. Reporting period differs from retrieval date. Amended
            filings preserve revisions.
          </p>
          <p>
            A filing address is not service geography; ZIP is not automatically
            ZCTA. Income context is not a direct measure of food insecurity.
          </p>
          <p>
            Sources preserve checksums, parser versions, locations,
            transformations, and access restrictions.
          </p>
        </Panel>
        <Panel title="Pilot boundaries">
          <p>
            The local demo uses fictional organizations and synthetic evidence.
            It does not establish real-world impact, partnerships, independently
            verified outcomes, or traction.
          </p>
          <p>
            Worldwide coverage, paid licensed data, billing, enterprise SSO,
            automatic grant submission, federated analysis, and validated
            distress models are outside this pilot.
          </p>
          <p>
            Production use requires security operations, backups, deployment
            safeguards, human pilot review, and real outcome validation.
          </p>
        </Panel>
      </div>
    </>
  );
}
