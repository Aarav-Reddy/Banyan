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
import {
  Benchmark,
  SaveEvidence,
  Attributions,
  PermittedContact,
} from "./pilot";
export function Dashboard() {
  const [expandedMatches, setExpandedMatches] = useState<string[]>([]);
  const { data, error } = useResource("dashboard/");
  const { data: recommendations } = useResource<Row[]>("recommendations/");
  return (
    <>
      <Header
        title="Overview"
        action={
          <Link className="button primary" href="/uploads">
            Upload program data
          </Link>
        }
      >
        Manage your programs, review data quality, and explore shared evidence.
      </Header>
      <State data={data} error={error}>
        {data && (
          <>
            <div className="workspace-summary">
              <dl className="record-metadata">
                <div>
                  <dt>Active programs</dt>
                  <dd>{data.programs.length}</dd>
                </div>
                <div>
                  <dt>Aggregate observations</dt>
                  <dd>{data.observation_count}</dd>
                </div>
              </dl>
              <p className="access-note">
                Contributor access · Core tools are free
              </p>
            </div>
            <div className="two-columns">
              <Panel
                title="Your program inventory"
                variant="open"
                aside={<Link href="/programs/new">Add program</Link>}
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
              <Panel title="Data quality">
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
            <Panel title="Evidence to investigate" variant="open">
              <p className="fine">
                Context-based transfer suggestions. Evidence strength,
                differences, and missing information remain separate.
              </p>
              {recommendations?.map((r) => (
                <div className="program-matches" key={r.program_id}>
                  <h3>{r.program_name}</h3>
                  {r.matches.matches?.length ? (
                    r.matches.matches
                      .slice(
                        0,
                        expandedMatches.includes(r.program_id) ? undefined : 6,
                      )
                      .map((m: Row) => (
                        <article className="recommendation" key={m.id}>
                          <div className="panel-heading">
                            <Link href={`/evidence/${m.id}`}>{m.title}</Link>
                            <Badge>{m.evidence_label}</Badge>
                          </div>
                          <p>{m.explanation}</p>
                          <details>
                            <summary>
                              Context matches, differences, failures and
                              adaptation questions
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
                  {r.matches.matches?.length > 6 && (
                    <button
                      type="button"
                      className="secondary"
                      aria-expanded={expandedMatches.includes(r.program_id)}
                      onClick={() =>
                        setExpandedMatches(
                          expandedMatches.includes(r.program_id)
                            ? expandedMatches.filter(
                                (id) => id !== r.program_id,
                              )
                            : [...expandedMatches, r.program_id],
                        )
                      }
                    >
                      {expandedMatches.includes(r.program_id)
                        ? "Show first six suggestions"
                        : `Show all ${r.matches.matches.length} context matches`}
                    </button>
                  )}
                </div>
              ))}
            </Panel>
            <Panel title="Compare compatible observations" variant="open">
              <p>
                Use fixed, permissioned cohort analyses to compare compatible
                observations. Missing reporting is never treated as poor
                performance.
              </p>
              <Link href="/analyses">Open combined analysis →</Link>
            </Panel>
            <Benchmark />
            <Panel
              title="Contributor support"
              variant="open"
              className="reading-column"
            >
              <p>
                Core contributor tools are free. Sponsored preparation requests
                are recorded for manual follow-up; no sponsor commitment is
                implied.
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
        title="Programs"
        action={
          <Link className="button primary" href="/programs/new">
            Add program
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
      <Header title={id ? "Edit program" : "Add program"}>
        Changes to program context invalidate dependent evidence and trigger
        fresh matching.
      </Header>
      <State data={programs} error={error}>
        <Form
          key={p?.id || "new"}
          className="form editor-form"
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
          <Panel title="Program profile" variant="open">
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
          <Panel title="Delivery context" variant="open">
            <p className="muted">
              Describe the setting and resources as reported. Leave unknown
              context blank.
            </p>
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
            <Panel title="Supporting source" variant="open">
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
        title="Evidence library"
        action={
          <Link className="button primary" href="/evidence/new">
            Draft evidence
          </Link>
        }
      >
        Implementation lessons, mixed results, and unanswered questions, with
        their sources intact.
      </Header>
      <div className="search-bar">
        <label htmlFor="evidence-search">Search evidence</label>
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
        <div className="evidence-list">
          {data?.map((c) => (
            <article className="evidence-card evidence-record" key={c.id}>
              <div className="evidence-record-body">
                <h2>
                  <Link href={`/evidence/${c.id}`}>{c.title}</Link>
                </h2>
                <p>
                  {c.payload.summary ||
                    "A structured implementation record; open to review the reported evidence and caveats."}
                </p>
                <dl className="record-metadata">
                  <div>
                    <dt>Population</dt>
                    <dd>{c.card.program.population}</dd>
                  </div>
                  <div>
                    <dt>Context</dt>
                    <dd>
                      {c.card.program.geography} · {c.card.program.intervention}
                    </dd>
                  </div>
                </dl>
                {c.card.failures && (
                  <p className="failure-note">
                    Mixed or failed results documented
                  </p>
                )}
                <Attributions artifact={c} />
              </div>
              <div className="evidence-record-aside">
                <dl className="record-metadata">
                  <div>
                    <dt>Evidence type</dt>
                    <dd>{c.card.evidence_label}</dd>
                  </div>
                  <div>
                    <dt>Editorial review</dt>
                    <dd>
                      <Badge>{c.status}</Badge>
                    </dd>
                  </div>
                  <div>
                    <dt>Data origin</dt>
                    <dd>
                      <Badge>{c.source_kind}</Badge>
                    </dd>
                  </div>
                </dl>
                <div className="actions">
                  <Link href={`/evidence/${c.id}`}>Read evidence →</Link>
                  <SaveEvidence id={c.id} />
                </div>
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
          <div className="evidence-metadata">
            <dl className="record-metadata">
              <div>
                <dt>Evidence type</dt>
                <dd>{data.card.evidence_label}</dd>
              </div>
              <div>
                <dt>Editorial review</dt>
                <dd>
                  <Badge>{data.status}</Badge> · Revision {data.revision}
                </dd>
              </div>
              <div>
                <dt>Data origin</dt>
                <dd>
                  <Badge>{data.source_kind}</Badge>
                </dd>
              </div>
            </dl>
            <SaveEvidence id={id} />
          </div>
          <div className="reading-column">
            <Panel title="Program and context" variant="open">
              <Details
                data={{
                  program: data.card.program.name,
                  cause: data.card.program.cause,
                  intervention: data.card.program.intervention,
                  population: data.card.program.population,
                  geography: data.card.program.geography,
                }}
              />
              <Details data={{ delivery_context: data.card.program.context }} />
              <details className="source-drawer">
                <summary>Complete program record and identifiers</summary>
                <Details data={data.card.program} />
              </details>
            </Panel>
            <Panel title="How to interpret this evidence" variant="open">
              <Details
                data={{
                  study_design: data.card.study_design,
                  attribution: data.card.attribution,
                }}
              />
              <Notice>
                Study design is separate from editorial review and repetition.
                An approved observational lesson does not become causal
                evidence.
              </Notice>
            </Panel>
            {[
              ["implementation_steps", "What was done"],
              ["barriers", "Operational barriers"],
              ["failures", "Failures and contradictory findings"],
              ["caveats", "Limitations and unanswered questions"],
            ].map(([k, t]) => (
              <Panel key={k} title={t} variant="open">
                <p className="preserve-lines">
                  {data.card[k] ||
                    "Not reported. Collect this information before applying the lesson."}
                </p>
              </Panel>
            ))}
          </div>
          <Attributions artifact={data} />
          <Sources sources={data.sources} />
          <Panel
            title="Source-grounded explanation"
            variant="open"
            className="reading-column"
          >
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
          {data.review && (
            <Panel title="Review of this revision" variant="open">
              <Details data={data.review} />
            </Panel>
          )}
          <div className="actions">
            <Link className="button secondary" href={`/reports/${id}`}>
              Printable evidence report
            </Link>
            <Link className="button secondary" href={`/graph?root=${id}`}>
              View connections
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
      <Header title={id ? "Edit evidence" : "Draft evidence"}>
        Record what happened, what failed, and what another organization should
        ask before adapting it.
      </Header>
      <State data={data} error={error}>
        <Form
          key={data?.id || "new"}
          className="form editor-form"
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
          <Panel title="Evidence overview" variant="open">
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
          <Panel title="Implementation and limitations" variant="open">
            <p className="muted">
              Include barriers and mixed results so readers can assess whether
              the lesson applies to their context.
            </p>
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
            <Panel title="Claim and supporting source" variant="open">
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
        title="Data uploads"
        action={
          <Link className="button secondary" href="/jobs">
            Background jobs
          </Link>
        }
      >
        Import aggregate outcomes and costs, or quarantine a report for manual
        evidence drafting.
      </Header>
      <div className="upload-layout">
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
            <p className="muted">
              Text and PDF reports stay quarantined for manual review. Extracted
              text does not automatically become validated outcome data.
            </p>
          </Form>
        </Panel>
        <Panel title="Templates and preparation" variant="open">
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
          <p className="muted">
            After upload, the worker checks your file. Aggregate files require
            column mapping and validation before you can commit records.
          </p>
        </Panel>
      </div>
      <Panel
        title="Import history"
        variant="open"
        aside={
          <button
            type="button"
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
    if (["queued", "processing"].includes(data?.status)) {
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
                type="button"
                className="secondary"
                onClick={() => setVersion(version + 1)}
              >
                Refresh status
              </button>
            }
          >
            Import status · <Badge>{data.status}</Badge>
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
            <Panel title="Column mapping" variant="open">
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
                <div className="mapping-grid">
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
                </div>
              </Form>
            </Panel>
          )}
          <Panel title="Validation results" variant="open">
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
          <Panel title="Preview · first records only" variant="open">
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
  const [version, setVersion] = useState(0);
  const { data: requests, error: requestError } = useResource<Row[]>(
    "requests/",
    version,
  );
  const { data: cards } = useResource<Row[]>("cards/");
  const recipients = new Map<string, string>();
  for (const c of cards || [])
    if (c.status === "approved")
      recipients.set(c.owner_id, c.card?.program?.name || c.title);
  return (
    <>
      <Header title="Funding opportunities">
        A limited curated catalogue. Matches use your stored cause and
        geography; verify all eligibility and deadlines with the funder.
      </Header>
      <State data={data} error={error}>
        {data?.map((o) => (
          <Panel key={o.id} title={o.title} variant="open">
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
          onSubmit={async (f) => {
            await mutate("requests/", "POST", {
              kind: "introduction",
              target_id: text(f, "target_id"),
              note: text(f, "note"),
            });
            setVersion(version + 1);
          }}
        >
          <Field label="Evidence contributor to contact" name="target_id">
            <select name="target_id" required>
              <option value="">Choose a permitted contributor</option>
              {Array.from(recipients).map(([id, name]) => (
                <option key={id} value={id}>
                  {name}
                </option>
              ))}
            </select>
          </Field>
          <Textarea
            label="Who would you like to learn from, and why?"
            name="note"
            required
          />
        </Form>
        <State data={requests} error={requestError}>
          {requests?.map((r) => (
            <div className="list-row" key={r.id}>
              <span>
                {label(r.kind)} · {r.note}
              </span>
              <Badge>{r.state}</Badge>
              {r.state === "accepted" && <PermittedContact id={r.id} />}
            </div>
          ))}
          {requests?.length === 0 && (
            <p className="fine">No introduction requests sent.</p>
          )}
        </State>
      </Panel>
    </>
  );
}
