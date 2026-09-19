"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  Row,
  ProgramRecord,
  mutate,
  money,
  date,
  label,
  api,
  download,
} from "@/lib/api";
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
  useResource,
  text,
  Action,
} from "./ui";
import { useWorkspace } from "./application";
export function Dashboard() {
  const { data, error } = useResource("dashboard/");
  const { data: recommendations } = useResource<Row[]>("recommendations/");
  return (
    <>
      <Header
        eyebrow="Nonprofit / Contributor workspace"
        title="Turn experience into shared learning."
        action={
          <Link className="button primary" href="/uploads">
            Contribute program data ↑
          </Link>
        }
      >
        A clear picture of your programs, the evidence you hold, and what to
        investigate next.
      </Header>
      <State data={data} error={error}>
        {data && (
          <>
            <div className="summary-strip">
              <div>
                <small>Active programs</small>
                <strong>{data.programs.length}</strong>
              </div>
              <div>
                <small>Aggregate observations</small>
                <strong>{data.observation_count}</strong>
              </div>
              <div>
                <small>Contributor access</small>
                <strong>Core tools · Free</strong>
              </div>
            </div>
            <div className="two-columns">
              <Panel
                title="Your program inventory"
                aside={<Link href="/programs/new">Add program +</Link>}
              >
                {data.programs.map((p: Row) => (
                  <div className="list-row" key={p.id}>
                    <div>
                      <Link href={`/programs/${p.id}`}>{p.name}</Link>
                      <p>
                        {p.intervention} · {p.geography}
                      </p>
                    </div>
                    <Badge>{p.cause}</Badge>
                  </div>
                ))}
                {!data.programs.length && (
                  <Empty title="Describe your first program" />
                )}
              </Panel>
              <Panel title="Improve the evidence picture">
                {data.data_quality.length ? (
                  <ul className="checklist">
                    {data.data_quality.map((s: string) => (
                      <li key={s}>{s}</li>
                    ))}
                  </ul>
                ) : (
                  <Notice tone="success">
                    The current data-quality checklist has no outstanding items.
                    This is not an independent quality certification.
                  </Notice>
                )}
                <Link href="/uploads">Review data & validation →</Link>
              </Panel>
            </div>
            <Panel title="Ideas to investigate">
              <p className="fine">
                Context-based transfer suggestions. Evidence strength,
                differences, and missing information remain separate.
              </p>
              {recommendations?.map((r) => (
                <div key={r.program_id}>
                  <h3>{r.program_name}</h3>
                  {r.matches.matches?.length ? (
                    r.matches.matches.map((m: Row) => (
                      <article className="recommendation" key={m.id}>
                        <div className="panel-heading">
                          <Link href={`/evidence/${m.id}`}>{m.title}</Link>
                          <Badge>{m.evidence_label}</Badge>
                        </div>
                        <p>{m.explanation}</p>
                        <details>
                          <summary>
                            Similarities, gaps & adaptation questions
                          </summary>
                          <Details
                            data={{
                              similarities: m.similarities,
                              differences: m.differences,
                              missing_context: m.missing_context,
                              failures: m.failures,
                              adaptation_questions: m.adaptation_questions,
                            }}
                          />
                        </details>
                      </article>
                    ))
                  ) : (
                    <Empty title="Insufficient compatible evidence">
                      Add program context and check again when permissioned
                      evidence becomes available.
                    </Empty>
                  )}
                </div>
              ))}
            </Panel>
            <div className="two-columns">
              <Panel title="Peer learning">
                <p>
                  Use fixed, permissioned cohort analyses to compare compatible
                  observations. Missing reporting is never treated as poor
                  performance.
                </p>
                <Link href="/analyses">Open pooled analysis →</Link>
              </Panel>
              <Panel title="Support for contributors">
                <p>
                  Core contributor tools are free. Sponsored preparation
                  requests are recorded for manual follow-up; no sponsor
                  commitment is implied.
                </p>
                <Form
                  submit="Request onboarding support"
                  onSubmit={(f) =>
                    mutate("requests/", "POST", {
                      kind: "sponsored_onboarding",
                      note: text(f, "note"),
                    })
                  }
                >
                  <Textarea
                    label="What help would be useful?"
                    name="note"
                    required
                  />
                </Form>
              </Panel>
            </div>
          </>
        )}
      </State>
    </>
  );
}
export function Programs() {
  const { data, error } = useResource<ProgramRecord[]>("programs/");
  return (
    <>
      <Header
        title="Your programs."
        action={
          <Link className="button primary" href="/programs/new">
            Add program +
          </Link>
        }
      >
        Describe the intervention and context before drawing comparisons.
      </Header>
      <State data={data} error={error}>
        {data?.length ? (
          <Panel>
            {data.map((p) => (
              <div className="list-row" key={p.id}>
                <div>
                  <Link href={`/programs/${p.id}`}>{p.name}</Link>
                  <p>
                    {p.intervention} · {p.population} · {p.geography}
                  </p>
                </div>
                <Badge>Revision {p.revision}</Badge>
                <Link href="/evidence/new">Draft evidence →</Link>
              </div>
            ))}
          </Panel>
        ) : (
          <Empty title="No programs yet">
            Add a source record and describe your program, or import aggregate
            observations.
          </Empty>
        )}
      </State>
    </>
  );
}
export function ProgramEditor({ id }: { id?: string }) {
  const router = useRouter();
  const { data: programs, error } = useResource<Row[]>("programs/");
  const ws = useWorkspace();
  const { data: sources } = useResource<Row[]>("sources/");
  const p = programs?.find((x) => x.id === id);
  return (
    <>
      <Header title={id ? "Edit program context." : "Describe a program."}>
        Changes to program context invalidate dependent evidence and trigger
        fresh matching.
      </Header>
      <State data={programs} error={error}>
        <Form
          key={p?.id || "new"}
          submit={id ? "Save program revision" : "Create program"}
          onSubmit={async (f) => {
            let source = text(f, "source_id");
            if (!id && !source) {
              const s = await mutate("sources/", "POST", {
                title: text(f, "source_title"),
                cause: text(f, "cause"),
                geography: text(f, "geography"),
                locator: text(f, "locator"),
              });
              source = s.id;
            }
            const body = {
              name: text(f, "name"),
              cause: text(f, "cause"),
              intervention: text(f, "intervention"),
              population: text(f, "population"),
              geography: text(f, "geography"),
              context: Object.fromEntries(
                [
                  "setting",
                  "infrastructure",
                  "resource_level",
                  "duration",
                  "language",
                  "delivery_partner",
                ]
                  .filter((k) => text(f, k))
                  .map((k) => [k, text(f, k)]),
              ),
              ...(id ? { revision: p?.revision } : { source_id: source }),
            };
            await mutate(
              id ? `programs/${id}/` : "programs/",
              id ? "PATCH" : "POST",
              body,
            );
            router.push("/programs");
          }}
        >
          <Panel title="Program profile">
            <div className="form-grid">
              {[
                ["name", "Program name", ""],
                ["cause", "Cause", "food_security"],
                ["intervention", "Intervention", ""],
                ["population", "Population", ""],
                ["geography", "Geography code", "US-MD-Baltimore"],
              ].map(([k, caption, v]) => (
                <Field
                  key={k}
                  name={k}
                  label={caption}
                  value={p?.[k] ?? v}
                  required
                />
              ))}
            </div>
          </Panel>
          <Panel title="Delivery context">
            <div className="form-grid">
              {[
                "setting",
                "infrastructure",
                "resource_level",
                "duration",
                "language",
                "delivery_partner",
              ].map((k) => (
                <Field
                  key={k}
                  name={k}
                  label={label(k)}
                  value={p?.context?.[k] || ""}
                />
              ))}
            </div>
          </Panel>
          {!id && (
            <Panel title="Supporting source">
              <Field label="Existing source (optional)" name="source_id">
                <select name="source_id">
                  <option value="">Create a manual source record</option>
                  {sources
                    ?.filter(
                      (s) => s.owner_id === ws.id && s.state === "active",
                    )
                    .map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.title}
                      </option>
                    ))}
                </select>
              </Field>
              <Field
                label="New source title"
                name="source_title"
                hint="Required when creating a manual source."
              />
              <Field
                label="Source location / section"
                name="locator"
                value="Program profile draft"
              />
            </Panel>
          )}
        </Form>
      </State>
    </>
  );
}
export function Cards() {
  const [search, setSearch] = useState("");
  const { data, error } = useResource<Row[]>(
    `cards/?q=${encodeURIComponent(search)}`,
  );
  return (
    <>
      <Header
        eyebrow="Shared learning / Permissioned evidence"
        title="What can we learn from each other?"
        action={
          <Link className="button primary" href="/evidence/new">
            Draft an intervention card +
          </Link>
        }
      >
        Implementation lessons, mixed results, and unanswered questions, with
        their sources intact.
      </Header>
      <div className="search-bar">
        <label className="sr-only" htmlFor="evidence-search">
          Search evidence
        </label>
        <input
          id="evidence-search"
          type="search"
          placeholder="Search interventions or evidence titles…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <span>Only currently permitted evidence</span>
      </div>
      <State data={data} error={error}>
        <div className="card-grid">
          {data?.map((c) => (
            <article className="evidence-card" key={c.id}>
              <div className="actions">
                <Badge>{c.card.evidence_label}</Badge>
                <Badge>{c.status}</Badge>
              </div>
              <h2>
                <Link href={`/evidence/${c.id}`}>{c.title}</Link>
              </h2>
              <p>
                {c.payload.summary ||
                  "A structured implementation record; open to review the reported evidence and caveats."}
              </p>
              <dl>
                <dt>Population</dt>
                <dd>{c.card.program.population}</dd>
                <dt>Context</dt>
                <dd>
                  {c.card.program.geography} · {c.card.program.intervention}
                </dd>
              </dl>
              {c.card.failures && (
                <p className="failure-note">
                  Mixed or failed results documented
                </p>
              )}
              <div className="org-card-footer">
                <Badge>{c.source_kind}</Badge>
                <Link href={`/evidence/${c.id}`}>Read evidence →</Link>
              </div>
            </article>
          ))}
        </div>
        {data?.length === 0 && (
          <Empty title="No permitted evidence matches">
            Broaden your search or contribute a sourced intervention card.
          </Empty>
        )}
      </State>
    </>
  );
}
export function Card({ id }: { id: string }) {
  const [version, setVersion] = useState(0),
    [explanation, setExplanation] = useState<Row | null>(null);
  const { data, error } = useResource(`cards/${id}/`, version);
  const ws = useWorkspace();
  return (
    <State data={data} error={error}>
      {data && (
        <>
          <Header
            eyebrow="Intervention evidence"
            title={data.title}
            action={
              data.owner_id === ws.id ? (
                <Link
                  className="button secondary"
                  href={`/evidence/${id}/edit`}
                >
                  Edit card
                </Link>
              ) : undefined
            }
          >
            {data.payload.summary}
          </Header>
          <div className="actions">
            <Badge>{data.card.evidence_label}</Badge>
            <Badge>{data.status}</Badge>
            <Badge>{data.source_kind}</Badge>
            <span>Revision {data.revision}</span>
          </div>
          <div className="two-columns">
            <Panel title="Program & context">
              <Details data={data.card.program} />
            </Panel>
            <Panel title="Evidence strength">
              <Details
                data={{
                  evidence_label: data.card.evidence_label,
                  study_design: data.card.study_design,
                  review_status: data.status,
                  attribution: data.card.attribution,
                }}
              />
              <Notice>
                Study design is separate from editorial review and repetition.
                An approved observational lesson does not become causal
                evidence.
              </Notice>
            </Panel>
          </div>
          {[
            ["implementation_steps", "Implementation guide"],
            ["barriers", "Operational barriers"],
            ["failures", "Failures & contradictory findings"],
            ["caveats", "Caveats & unanswered questions"],
          ].map(([k, t]) => (
            <Panel key={k} title={t}>
              <p className="preserve-lines">
                {data.card[k] ||
                  "Not reported. Collect this information before applying the lesson."}
              </p>
            </Panel>
          ))}
          <Panel title="Source-grounded explanation">
            <p>
              Deterministic explanations work without a model. Any optional
              generated synthesis must retain permitted citations.
            </p>
            <Action
              run={async () =>
                setExplanation(await mutate(`explanations/${id}/`, "POST", {}))
              }
            >
              Explain this evidence
            </Action>
            {explanation && (
              <>
                <Badge>{explanation.mode}</Badge>
                <p>{explanation.reason}</p>
                {explanation.claims?.map((c: Row, i: number) => (
                  <div className="source" key={i}>
                    <p>{c.text}</p>
                    <Link href={`/sources/${c.source_id}`}>
                      {c.locator || "Supporting source"}
                    </Link>
                    <Badge>{c.evidence_label}</Badge>
                  </div>
                ))}
                {explanation.questions?.map((q: string) => (
                  <p key={q}>{q}</p>
                ))}
              </>
            )}
          </Panel>
          {data.owner_id === ws.id && (
            <ReviewSubmit
              artifact={data}
              onSaved={() => setVersion(version + 1)}
            />
          )}
          <Sources sources={data.sources} />
          {data.review && (
            <Panel title="Version-bound review">
              <Details data={data.review} />
            </Panel>
          )}
          <div className="actions">
            <Link className="button secondary" href={`/reports/${id}`}>
              Printable evidence report
            </Link>
            <Link className="button secondary" href={`/graph?root=${id}`}>
              Explore relationships
            </Link>
          </div>
        </>
      )}
    </State>
  );
}
const EVIDENCE = [
  "descriptive observation",
  "correlation",
  "quasi-experimental finding",
  "randomized evaluation",
  "repeated cross-organization pattern",
  "expert-reviewed operational lesson",
  "early hypothesis",
];
export function CardEditor({ id }: { id?: string }) {
  const router = useRouter();
  const { data: programs } = useResource<Row[]>("programs/");
  const { data: sources } = useResource<Row[]>("sources/");
  const { data, error } = useResource(id ? `cards/${id}/` : "dashboard/");
  return (
    <>
      <Header
        title={
          id
            ? "Revise the implementation lesson."
            : "Draft a sourced intervention card."
        }
      >
        Record what happened, what failed, and what another organization should
        ask before adapting it.
      </Header>
      <State data={data} error={error}>
        <Form
          key={data?.id || "new"}
          submit={id ? "Save new revision" : "Save private draft"}
          onSubmit={async (f) => {
            const fields = Object.fromEntries(
              [
                "title",
                "implementation_steps",
                "barriers",
                "failures",
                "caveats",
                "attribution",
              ].map((k) => [k, text(f, k)]),
            );
            const body = id
              ? { ...fields, revision: data?.revision }
              : {
                  ...fields,
                  program_id: text(f, "program_id"),
                  summary: text(f, "summary"),
                  evidence_label: text(f, "evidence_label"),
                  study_design: text(f, "study_design"),
                  claims: text(f, "claim")
                    ? [
                        {
                          text: text(f, "claim"),
                          source_id: text(f, "claim_source"),
                          locator: text(f, "locator"),
                          label: text(f, "evidence_label"),
                        },
                      ]
                    : [],
                };
            const c = await mutate(
              id ? `cards/${id}/` : "cards/",
              id ? "PATCH" : "POST",
              body,
            );
            router.push(`/evidence/${c.id}`);
          }}
        >
          <Panel title="The lesson">
            <Field
              label="Card title"
              name="title"
              value={data?.title}
              required
            />
            {!id && (
              <>
                <Field label="Program" name="program_id">
                  <select required name="program_id">
                    <option value="">Choose a program</option>
                    {programs?.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))}
                  </select>
                </Field>
                <Textarea label="Summary" name="summary" required />
                <div className="form-grid">
                  <Field label="Evidence label" name="evidence_label">
                    <select name="evidence_label">
                      {EVIDENCE.map((x) => (
                        <option key={x}>{x}</option>
                      ))}
                    </select>
                  </Field>
                  <Field label="Underlying study design" name="study_design">
                    <select name="study_design">
                      <option value="observational">Observational</option>
                      <option value="quasi_experimental">
                        Quasi-experimental
                      </option>
                      <option value="randomized">Randomized</option>
                      <option value="unknown">Unknown</option>
                    </select>
                  </Field>
                </div>
              </>
            )}
          </Panel>
          <Panel title="Implementation & limitations">
            {[
              ["implementation_steps", "Implementation steps"],
              ["barriers", "Operational barriers"],
              [
                "failures",
                "Failures, discontinuations or contradictory findings",
              ],
              ["caveats", "Caveats and evidence gaps"],
              ["attribution", "Attribution requirements"],
            ].map(([k, t]) => (
              <Textarea
                key={k}
                label={t}
                name={k}
                value={data?.card?.[k] || ""}
              />
            ))}
          </Panel>
          {!id && (
            <Panel title="A traceable substantive claim">
              <Textarea label="Claim supported by the source" name="claim" />
              <Field label="Supporting source" name="claim_source">
                <select name="claim_source">
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
              <Field label="Page, row, or field locator" name="locator" />
              <p className="fine">
                Every supplied claim needs both source and locator. Unsupported
                interpretation belongs in caveats as an early hypothesis.
              </p>
            </Panel>
          )}
        </Form>
      </State>
    </>
  );
}
export function Uploads() {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource<Row[]>("imports/", version);
  const router = useRouter();
  return (
    <>
      <Header
        title="Bring your evidence together."
        action={
          <Link className="button secondary" href="/jobs">
            Worker & job status ↗
          </Link>
        }
      >
        Import aggregate outcomes and costs, or quarantine a report for manual
        evidence drafting.
      </Header>
      <div className="two-columns">
        <Panel title="Upload a source">
          <Form
            submit="Upload to quarantine"
            onSubmit={async (f) => {
              const result = await api("imports/", { method: "POST", body: f });
              router.push(`/uploads/${result.id}`);
            }}
          >
            <Field
              name="file"
              type="file"
              label="CSV, XLSX, text report, or text PDF"
              accept=".csv,.xlsx,.txt,.pdf"
              required
            />
            <Notice>
              Aggregate data only. Do not upload beneficiary names, contact
              details, identifiers, or sensitive individual records. Maximum 5
              MiB.
            </Notice>
          </Form>
        </Panel>
        <Panel title="Start with a supported template">
          <p>
            Keep outcome definitions, units, denominators, periods, and cohort
            independence explicit. Unknown values remain unknown.
          </p>
          <div className="actions">
            <Action
              run={() =>
                download(
                  "import-template/?kind=outcome",
                  "aggregate-outcomes.csv",
                )
              }
            >
              Outcome template ↓
            </Action>
            <Action
              run={() =>
                download("import-template/?kind=cost", "aggregate-costs.csv")
              }
            >
              Cost template ↓
            </Action>
          </div>
          <p className="fine">
            Reports stay quarantined. Extracted text does not automatically
            become validated outcome data.
          </p>
        </Panel>
      </div>
      <Panel
        title="Import history"
        aside={
          <button
            className="text-button"
            onClick={() => setVersion(version + 1)}
          >
            Refresh
          </button>
        }
      >
        <State data={data} error={error}>
          {data?.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>File</th>
                    <th>Format</th>
                    <th>Stage</th>
                    <th>Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((b) => (
                    <tr key={b.id}>
                      <td>
                        <Link href={`/uploads/${b.id}`}>{b.filename}</Link>
                      </td>
                      <td>{b.format.toUpperCase()}</td>
                      <td>
                        <Badge>{b.status}</Badge>
                      </td>
                      <td>{date(b.created_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty title="No imports yet" />
          )}
        </State>
      </Panel>
    </>
  );
}
const FIELDS = [
  "record_type",
  "program_name",
  "cause",
  "intervention",
  "population",
  "geography",
  "period_start",
  "period_end",
  "outcome_code",
  "outcome_definition",
  "unit",
  "direction",
  "numerator",
  "denominator",
  "cohort_id",
  "study_id",
  "independent",
  "followup_months",
  "comparator",
  "study_design",
  "uncertainty",
  "missingness",
  "stratum",
  "amount",
  "currency",
];
export function ImportDetail({ id }: { id: string }) {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource(`imports/${id}/`, version);
  const [columns, setColumns] = useState<string[]>([]);
  useEffect(() => {
    if (data?.status === "queued") {
      const t = setTimeout(() => setVersion((v) => v + 1), 3000);
      return () => clearTimeout(t);
    }
  }, [data]);
  const detected: string[] =
    data?.columns ||
    data?.preview?.columns ||
    data?.diagnostics?.find((d: Row) => d.columns)?.columns ||
    columns;
  return (
    <State data={data} error={error}>
      {data && (
        <>
          <Header
            title={data.filename}
            action={
              <button
                className="secondary"
                onClick={() => setVersion(version + 1)}
              >
                Refresh status
              </button>
            }
          >
            Secure onboarding · <Badge>{data.status}</Badge>
          </Header>
          <Notice>
            {data.status === "needs_mapping"
              ? "Map each input column explicitly. No column is silently ignored."
              : data.status === "quarantined"
                ? "This report is quarantined. Review extracted text and draft a structured evidence card manually."
                : data.status === "completed"
                  ? "Normalized records were persisted. Repeating this import will not duplicate them."
                  : "Validation and persistence are performed by the background worker."}
          </Notice>
          {["needs_mapping", "partial", "invalid"].includes(data.status) && (
            <Panel title="Column mapping">
              <p>
                Map input headers to the supported aggregate fields. If headers
                are unavailable, paste the comma-separated header row only.
              </p>
              <label className="field">
                <span>Input column headers</span>
                <input
                  placeholder="program_name,outcome_code,numerator,…"
                  onChange={(e) =>
                    setColumns(
                      e.target.value
                        .split(",")
                        .map((x) => x.trim())
                        .filter(Boolean),
                    )
                  }
                />
              </label>
              <Form
                submit="Validate mapping"
                onSubmit={async (f) => {
                  await mutate(`imports/${id}/`, "PATCH", {
                    mapping: Object.fromEntries(
                      detected.map((c, i) => [c, text(f, `column_${i}`)]),
                    ),
                  });
                  setVersion(version + 1);
                }}
              >
                {detected.map((c, i) => (
                  <Field key={c} label={c} name={`column_${i}`}>
                    <select
                      required
                      name={`column_${i}`}
                      defaultValue={
                        data.mapping?.[c] || (FIELDS.includes(c) ? c : "")
                      }
                    >
                      <option value="">Select normalized field</option>
                      {FIELDS.map((f) => (
                        <option key={f}>{f}</option>
                      ))}
                    </select>
                  </Field>
                ))}
              </Form>
            </Panel>
          )}
          <Panel title="Validation results">
            {data.diagnostics?.length ? (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Location</th>
                      <th>Severity</th>
                      <th>Issue</th>
                      <th>Next step</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.diagnostics.map((d: Row, i: number) => (
                      <tr key={i}>
                        <td>
                          {d.row || d.locator || "File"} {d.field}
                        </td>
                        <td>
                          <Badge>{d.severity || "information"}</Badge>
                        </td>
                        <td>{d.code}</td>
                        <td>{d.message}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p>No row-level issues reported at this stage.</p>
            )}
            <Action
              run={() =>
                download(`imports/${id}/rejected/`, "validation-issues.csv")
              }
            >
              Download validation issues ↓
            </Action>
          </Panel>
          <Panel title="Preview · first records only">
            {Array.isArray(data.preview) && data.preview.length ? (
              data.preview.map((r: Row, i: number) => (
                <details className="source-drawer" key={i}>
                  <summary>
                    {r.program_name || r.locator || `Record ${i + 1}`}
                  </summary>
                  <Details data={r} />
                </details>
              ))
            ) : (
              <Empty title="No preview available yet">
                Queued jobs may need a running worker. Failed validation may
                prevent preview.
              </Empty>
            )}
          </Panel>
          {data.status === "validated" && (
            <Action
              run={async () => {
                await mutate(`imports/${id}/commit/`, "POST");
                setVersion(version + 1);
              }}
            >
              Commit validated records
            </Action>
          )}
          {data.status === "quarantined" && (
            <Link className="button primary" href="/evidence/new">
              Draft evidence from this source →
            </Link>
          )}
          <Link className="button secondary" href="/jobs">
            Inspect processing jobs
          </Link>
        </>
      )}
    </State>
  );
}
export function Opportunities() {
  const { data, error } = useResource<Row[]>("opportunities/");
  const { data: requests } = useResource<Row[]>("requests/");
  return (
    <>
      <Header title="Funding opportunities, with context.">
        A limited curated catalogue. Matches use your stored cause and
        geography; verify all eligibility and deadlines with the funder.
      </Header>
      <State data={data} error={error}>
        {data?.map((o) => (
          <Panel key={o.id} title={o.title}>
            <div className="actions">
              <Badge>{o.source.kind}</Badge>
              <Badge>{o.freshness}</Badge>
              <Badge>
                {o.matched ? "Profile match" : "Review eligibility"}
              </Badge>
            </div>
            <p>{o.eligibility}</p>
            <p>{o.explanation}</p>
            <Details
              data={{
                deadline: o.deadline,
                amount: money(o.amount_cents, true),
                geography: o.geography,
                cause: o.cause,
              }}
            />
            <Sources sources={[o.source]} />
          </Panel>
        ))}
        {data?.length === 0 && <Empty title="No permitted opportunities" />}
      </State>
      <Panel title="Request an introduction">
        <p>
          Requests are saved for manual follow-up. No outbound message is sent,
          and no contact or partnership is implied.
        </p>
        <Form
          submit="Save introduction request"
          onSubmit={(f) =>
            mutate("requests/", "POST", {
              kind: "introduction",
              note: text(f, "note"),
            })
          }
        >
          <Textarea
            label="Who would you like to learn from, and why?"
            name="note"
            required
          />
        </Form>
        {requests?.map((r) => (
          <div className="list-row" key={r.id}>
            <span>
              {label(r.kind)} · {r.note}
            </span>
            <Badge>{r.state}</Badge>
          </div>
        ))}
      </Panel>
    </>
  );
}
