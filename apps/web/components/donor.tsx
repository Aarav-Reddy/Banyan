"use client";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useRef, useState } from "react";
import {
  Row,
  OrganizationRecord,
  money,
  date,
  label,
  mutate,
  toCents,
  dollars,
} from "@/lib/api";
import {
  useResource,
  Header,
  Panel,
  State,
  Empty,
  Notice,
  Badge,
  Field,
  Form,
  Details,
  Sources,
  ReviewSubmit,
  ExportButton,
  text,
} from "./ui";
import { useWorkspace } from "./application";
import { CommunityContext, WatchOrganization, Attributions } from "./pilot";
export function Discovery() {
  const query = useSearchParams(),
    router = useRouter();
  const { data, error } = useResource<OrganizationRecord[]>(
    `organizations/?${query.toString()}`,
  );
  const { data: geographies } = useResource<Row[]>("geographies/");
  const [selected, setSelected] = useState<string[]>([]),
    [focus, setFocus] = useState(""),
    [view, setView] = useState("list");
  const advancedFilters = useRef<HTMLDetailsElement>(null);
  const [advancedCount, setAdvancedCount] = useState(
    () =>
      [
        "population",
        "size",
        "budget_cents",
        "risk",
        "outcome_definition",
        "horizon_days",
      ].filter(
        (key) =>
          query.get(key) && !(key === "risk" && query.get(key) === "all"),
      ).length,
  );
  return (
    <>
      <Header
        eyebrow="Baltimore food-security pilot"
        title="Find nonprofits"
        action={
          <Link className="button secondary" href="/portfolios">
            Funding plans
          </Link>
        }
      >
        Investigate organizations through their work, financial context, and
        available evidence.
      </Header>
      <Form
        className="filter-panel"
        submit="Apply filters"
        success="Filters applied."
        onSubmit={async (f) => {
          const p = new URLSearchParams();
          for (const k of [
            "q",
            "cause",
            "location",
            "population",
            "size",
            "risk",
            "outcome_definition",
            "horizon_days",
          ])
            if (text(f, k)) p.set(k, text(f, k));
          if (text(f, "budget")) {
            try {
              p.set("budget_cents", String(toCents(text(f, "budget"))));
            } catch (error) {
              if (advancedFilters.current) {
                advancedFilters.current.open = true;
                advancedFilters.current
                  .querySelector<HTMLInputElement>('[name="budget"]')
                  ?.focus();
              }
              throw error;
            }
          }
          router.push(`/discover?${p}`);
        }}
      >
        <div className="discovery-primary-filters">
          <Field
            name="q"
            label="Organization"
            value={query.get("q") || ""}
            placeholder="Search by name"
          />
          <Field name="cause" label="Cause">
            <select name="cause" defaultValue={query.get("cause") || ""}>
              <option value="">All causes</option>
              <option value="food_security">Food security</option>
            </select>
          </Field>
          <Field name="location" label="Service area">
            <select name="location" defaultValue={query.get("location") || ""}>
              <option value="">All reported areas</option>
              {geographies?.map((g) => (
                <option key={g.code} value={g.code}>
                  {g.name} ({g.kind})
                </option>
              ))}
            </select>
          </Field>
        </div>
        <details
          className="advanced-filters"
          ref={advancedFilters}
          onInvalidCapture={(event) => {
            event.currentTarget.open = true;
          }}
          onChange={(event) => {
            const controls = event.currentTarget.querySelectorAll<
              HTMLInputElement | HTMLSelectElement
            >("input, select");
            setAdvancedCount(
              Array.from(controls).filter(
                (control) =>
                  control.value &&
                  !(control.name === "risk" && control.value === "all"),
              ).length,
            );
          }}
        >
          <summary>
            More filters
            <span className="advanced-filter-count">
              {advancedCount
                ? `${advancedCount} additional ${advancedCount === 1 ? "filter" : "filters"} set`
                : "6 options"}
            </span>
          </summary>
          <div className="form-grid">
            <Field
              name="population"
              label="Population"
              value={query.get("population") || ""}
              placeholder="e.g. households"
            />
            <Field name="size" label="Annual revenue">
              <select name="size" defaultValue={query.get("size") || ""}>
                <option value="">All reported sizes</option>
                <option value="small">Under $500,000</option>
                <option value="medium">$500,000–$2 million</option>
                <option value="large">$2 million and above</option>
              </select>
            </Field>
            <Field
              name="budget"
              label="Planning budget (USD)"
              value={
                query.get("budget_cents")
                  ? dollars(Number(query.get("budget_cents")))
                  : ""
              }
              placeholder="25000.00"
              inputMode="decimal"
            />
            <Field name="risk" label="Financial preference">
              <select name="risk" defaultValue={query.get("risk") || "all"}>
                <option value="all">Investigate all signals</option>
                <option value="avoid_repeated_deficits">
                  Exclude repeated-deficit flags
                </option>
                <option value="capacity_building">
                  Investigate capacity-building needs
                </option>
              </select>
            </Field>
            <Field
              name="outcome_definition"
              label="Desired outcome code"
              value={query.get("outcome_definition") || ""}
              placeholder="e.g. food_security_improved"
            />
            <Field
              name="horizon_days"
              label="Maximum follow-up (days)"
              type="number"
              min="1"
              max="3650"
              value={query.get("horizon_days") || ""}
              placeholder="e.g. 180"
            />
          </div>
        </details>
      </Form>
      <div className="results-toolbar">
        <div>
          <strong>{data?.length ?? "…"} organizations</strong>
          <span className="muted">
            {" "}
            · Reported service areas, not headquarters
          </span>
        </div>
        <div className="segmented" aria-label="Result display">
          {["list", "table"].map((v) => (
            <button
              key={v}
              type="button"
              aria-pressed={view === v}
              onClick={() => setView(v)}
            >
              {label(v)}
            </button>
          ))}
        </div>
      </div>
      <State data={data} error={error}>
        {data && data.length === 0 ? (
          <Empty title="No organizations match these filters">
            Try a broader service area or revenue range. Unknown geography and
            missing financial records are never filled with invented matches.
          </Empty>
        ) : (
          <div className="discovery-grid">
            <section aria-label="Organization results">
              {view === "table" ? (
                <div
                  className="table-wrap"
                  role="region"
                  aria-label="Organization results table"
                  tabIndex={0}
                >
                  <table>
                    <thead>
                      <tr>
                        <th>Compare</th>
                        <th>Organization</th>
                        <th>Revenue</th>
                        <th>Period</th>
                        <th>Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {data?.map((o) => (
                        <tr key={o.id}>
                          <td>
                            <input
                              type="checkbox"
                              aria-label={`Compare ${o.name}`}
                              checked={selected.includes(o.id)}
                              disabled={
                                !selected.includes(o.id) &&
                                selected.length === 4
                              }
                              onChange={() =>
                                setSelected(
                                  selected.includes(o.id)
                                    ? selected.filter((x) => x !== o.id)
                                    : [...selected, o.id],
                                )
                              }
                            />
                          </td>
                          <td>
                            <Link href={`/organizations/${o.id}`}>
                              {o.name}
                            </Link>
                          </td>
                          <td className="numeric">
                            {money(o.latest_filing?.revenue)}
                          </td>
                          <td>{o.latest_filing?.tax_year || "Unknown"}</td>
                          <td>
                            <Badge>{o.source_kind}</Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                data?.map((o, i) => (
                  <article
                    className={`org-card ${focus === o.id ? "focused" : ""}`}
                    key={o.id}
                    onMouseEnter={() => setFocus(o.id)}
                  >
                    <div className="org-card-top">
                      <span
                        className="org-mark"
                        aria-label={`List position ${i + 1}`}
                      >
                        {String(i + 1).padStart(2, "0")}
                      </span>
                      <div>
                        <h2 className="org-name">
                          <Link
                            className="org-title"
                            href={`/organizations/${o.id}`}
                          >
                            {o.name}
                          </Link>
                        </h2>
                        <p>
                          {o.service_areas
                            .map((g: Row) => g.name)
                            .join(" · ") || "Service geography not reported"}
                        </p>
                      </div>
                      <label className="check-label">
                        <input
                          type="checkbox"
                          checked={selected.includes(o.id)}
                          disabled={
                            !selected.includes(o.id) && selected.length === 4
                          }
                          onChange={() =>
                            setSelected(
                              selected.includes(o.id)
                                ? selected.filter((x) => x !== o.id)
                                : [...selected, o.id],
                            )
                          }
                        />
                        Compare
                      </label>
                    </div>
                    <p className="org-mission">{o.mission}</p>
                    <div className="org-stats">
                      <div>
                        <small>
                          Annual revenue ·{" "}
                          {o.latest_filing?.tax_year || "unknown"}
                        </small>
                        <strong>{money(o.latest_filing?.revenue)}</strong>
                      </div>
                      <div>
                        <small>Reported funding capacity</small>
                        <strong>{money(o.capacity_cents, true)}</strong>
                      </div>
                      <div>
                        <small>Evidence & financial signals</small>
                        <Link href={`/organizations/${o.id}`}>
                          View profile
                        </Link>
                      </div>
                    </div>
                    <DiscoverySummary
                      summary={(o as unknown as Row).discovery_summary}
                    />
                    <div className="org-card-footer">
                      <Badge>{o.source_kind}</Badge>
                      <span>
                        Retrieved {date(o.latest_filing?.source?.retrieved_at)}
                      </span>
                    </div>
                  </article>
                ))
              )}
            </section>
            <aside className="map-panel">
              <div className="panel-heading">
                <h2>Service-area context</h2>
                <Badge>Schematic</Badge>
              </div>
              <svg
                viewBox="0 0 400 420"
                role="group"
                aria-label="Schematic of reported Baltimore service areas. Use the organization list for precise labels."
              >
                <rect width="400" height="420" fill="#eef0e8" />
                <path
                  d="M270 0L242 75 278 130 255 205 305 270 280 335 332 420H400V0"
                  fill="#d3e3e4"
                />
                <g stroke="#d5d9cb" fill="none" strokeWidth="2">
                  <path d="M0 105L400 145M0 235L400 270M80 0L150 420M220 0L200 420M0 330L280 30" />
                  <path
                    d="M10 10L70 160 35 295 240 390M120 70L330 330"
                    strokeWidth="10"
                    stroke="#f8f8f0"
                  />
                </g>
                <text x="90" y="205" className="map-text">
                  BALTIMORE
                </text>
                <text
                  x="298"
                  y="235"
                  className="map-water"
                  transform="rotate(65 298 235)"
                >
                  CHESAPEAKE
                </text>
                {data
                  ?.filter((o) => o.service_areas.length)
                  .slice(0, 20)
                  .map((o, i) => (
                    <g
                      key={o.id}
                      tabIndex={0}
                      role="button"
                      aria-label={`Highlight ${o.name}`}
                      onClick={() => setFocus(o.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") setFocus(o.id);
                      }}
                      onFocus={() => setFocus(o.id)}
                    >
                      <circle
                        cx={65 + (i % 4) * 54 + (Math.floor(i / 4) % 2) * 18}
                        cy={65 + Math.floor(i / 4) * 63}
                        r={focus === o.id ? 17 : 13}
                        fill={focus === o.id ? "#b57632" : "#164c42"}
                        stroke="white"
                        strokeWidth="3"
                      />
                      <text
                        x={65 + (i % 4) * 54 + (Math.floor(i / 4) % 2) * 18}
                        y={69 + Math.floor(i / 4) * 63}
                        textAnchor="middle"
                        fill="white"
                        fontSize="10"
                      >
                        {i + 1}
                      </text>
                    </g>
                  ))}
              </svg>
              <p className="map-note">
                Offline schematic · Points correspond to list order, not exact
                coordinates or verified boundaries. Numbers are positions, not
                rankings. No inference of unmet need.
              </p>
              {focus && (
                <div className="map-selected">
                  <strong>{data?.find((o) => o.id === focus)?.name}</strong>
                  <Link href={`/organizations/${focus}`}>View profile →</Link>
                </div>
              )}
              <div className="map-legend">
                <span className="dot" /> Organizations with reported service
                areas
              </div>
              <CommunityContext geographies={geographies || []} />
            </aside>
          </div>
        )}
      </State>
      <Notice>
        Discovery is a starting point for investigation. Outcome and horizon
        filters require permitted observations. Missing financial history is
        unknown, not financial resilience; absent reporting is not
        ineffectiveness. No universal risk or impact ranking is applied.
      </Notice>
      {selected.length > 0 && (
        <div className="selection-bar">
          <span>
            <strong>{selected.length}</strong> of 4 selected
          </span>
          {selected.length >= 2 ? (
            <Link
              className="button secondary"
              href={`/compare?ids=${selected.join(",")}`}
            >
              Compare organizations
            </Link>
          ) : (
            <span>Select one more to compare</span>
          )}
          <Link
            className="button primary"
            href={`/allocate?ids=${selected.join(",")}`}
          >
            Plan funding
          </Link>
          <button
            type="button"
            className="text-button"
            onClick={() => setSelected([])}
          >
            Clear selection
          </button>
        </div>
      )}
    </>
  );
}
export function DiscoverySummary({ summary }: { summary?: Row }) {
  if (!summary)
    return (
      <p className="fine">
        Financial summary unavailable; inspect the source records.
      </p>
    );
  const share = summary.program_spending_share;
  return (
    <div className="discovery-summary">
      <div className="actions">
        <span>
          <strong>Program-spending share:</strong>{" "}
          {share?.value == null
            ? "Unknown"
            : new Intl.NumberFormat("en-US", {
                style: "percent",
                maximumFractionDigits: 1,
              }).format(Number(share.value))}
        </span>
        <span>
          <strong>Approved evidence cards:</strong>{" "}
          {summary.approved_evidence_cards}
        </span>
      </div>
      {share?.value == null && share?.reason && (
        <p className="fine">{share.reason}</p>
      )}
      <p className="fine">
        {summary.evidence_caveat} Program-spending share is not an impact
        measure.
      </p>
      {summary.financial_flags?.length > 0 && (
        <ul className="signal-list">
          {summary.financial_flags.map((f: Row) => (
            <li key={f.code}>
              <Badge>{f.state}</Badge> <strong>{label(f.code)}</strong>:{" "}
              {f.explanation}
            </li>
          ))}
        </ul>
      )}
      {summary.missing_fields?.length > 0 && (
        <p className="fine">
          Missing financial fields:{" "}
          {summary.missing_fields.map(label).join(", ")}. Missing is not zero.
        </p>
      )}
    </div>
  );
}
export function Organization({ id }: { id: string }) {
  const { data, error } = useResource(`organizations/${id}/`);
  return (
    <State data={data} error={error}>
      {data && (
        <>
          <Header
            eyebrow="Organization profile"
            title={data.organization.name}
            action={
              <Link className="button primary" href={`/allocate?ids=${id}`}>
                Add to funding plan →
              </Link>
            }
          >
            {data.organization.mission}
          </Header>
          <div className="actions">
            <WatchOrganization id={id} />
            <Badge>{data.organization.source_kind}</Badge>
            <Badge>{data.organization.status}</Badge>
            <span>
              {label(data.organization.cause)} · {data.organization.country}
            </span>
          </div>
          <div className="two-columns">
            <Panel title="Organization and reported context" variant="open">
              <dl className="profile-facts">
                <div>
                  <dt>Population served</dt>
                  <dd>{data.organization.population || "Not reported"}</dd>
                </div>
                <div>
                  <dt>Headquarters ZIP</dt>
                  <dd>
                    {data.organization.headquarters_zip || "Not reported"}
                  </dd>
                </div>
                <div>
                  <dt>Reported funding capacity</dt>
                  <dd>{money(data.organization.capacity_cents, true)}</dd>
                </div>
                <div>
                  <dt>Capacity context</dt>
                  <dd>{data.organization.capacity_note || "Not reported"}</dd>
                </div>
              </dl>
              <h3>Reported service areas</h3>
              <p className="fine">
                Service areas are separate from the headquarters address.
              </p>
              {data.organization.service_areas.length ? (
                data.organization.service_areas.map(
                  (area: Row, index: number) => (
                    <div className="service-area-record" key={index}>
                      <h4>{area.name}</h4>
                      <Details
                        data={{
                          basis: area.basis,
                          kind: area.kind,
                          context: area.context,
                        }}
                      />
                    </div>
                  ),
                )
              ) : (
                <p>Not reported</p>
              )}
            </Panel>
            <Panel title="Financial warning signals" variant="open">
              <p className="fine">
                Transparent policy signals, not a probability of collapse.
                Method {data.financial_signals.method_version}.
              </p>
              {data.financial_signals.signals?.map((s: Row, i: number) => (
                <div className="signal" key={i}>
                  <Badge>{s.state}</Badge>
                  <strong>{label(s.code)}</strong>
                  <p>{s.explanation}</p>
                  {s.threshold && (
                    <small>Threshold: {String(s.threshold)}</small>
                  )}
                </div>
              ))}
            </Panel>
          </div>
          <Panel title="Financial history" variant="open">
            <p className="fine">
              Financial values in USD. Program spending does not measure
              outcomes or impact. Revisions and fiscal periods are preserved.
            </p>
            <div
              className="table-wrap"
              role="region"
              aria-label="Financial history"
              tabIndex={0}
            >
              <table>
                <thead>
                  <tr>
                    <th>Tax year / form</th>
                    <th>Revenue</th>
                    <th>Expenses</th>
                    <th>Program expenses</th>
                    <th>Assets</th>
                    <th>Liabilities</th>
                    <th>Revision</th>
                  </tr>
                </thead>
                <tbody>
                  {data.filings.map((f: Row) => (
                    <tr key={f.id}>
                      <td>
                        {f.tax_year} · {f.form}
                        <small>
                          {f.period_start} – {f.period_end}
                        </small>
                      </td>
                      {[
                        "revenue",
                        "expenses",
                        "program_expenses",
                        "assets",
                        "liabilities",
                      ].map((k) => (
                        <td key={k} className="numeric">
                          {money(f[k])}
                        </td>
                      ))}
                      <td>
                        {f.revision} {f.active ? "active" : "superseded"}
                        {f.amended ? " · amended" : ""}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!data.filings.length && (
              <Empty title="Financial filings unavailable" />
            )}
            <details className="source-drawer">
              <summary>Calculated ratios, missingness & assumptions</summary>
              {data.financial_signals.periods?.map((p: Row) => (
                <Panel key={p.id} title={String(p.tax_year)}>
                  <Details data={p.metrics} />
                  <p>{p.caveats?.join(" · ")}</p>
                </Panel>
              ))}
            </details>
            <Sources sources={data.filings.map((f: Row) => f.source)} />
          </Panel>
          <Panel title="Programs and permitted evidence" variant="open">
            {data.programs.map((p: Row) => (
              <div className="list-row" key={p.id}>
                <div>
                  <h3>{p.name}</h3>
                  <p>
                    {p.intervention} · {p.population} · {p.geography}
                  </p>
                </div>
              </div>
            ))}
            {data.cards.map((c: Row) => (
              <div className="list-row" key={c.id}>
                <Link href={`/evidence/${c.id}`}>{c.title}</Link>
                <Badge>{c.card.evidence_label}</Badge>
                <Badge>{c.status}</Badge>
              </div>
            ))}
            {!data.cards.length && (
              <Empty title="No permitted evidence cards">
                Unavailable evidence is not evidence of ineffectiveness.
              </Empty>
            )}
          </Panel>
        </>
      )}
    </State>
  );
}
export function Compare() {
  const p = useSearchParams();
  const { data, error } = useResource(`compare/?ids=${p.get("ids") || ""}`);
  return (
    <>
      <Header
        title="Compare organizations"
        action={
          <Link
            className="button primary"
            href={`/allocate?ids=${p.get("ids") || ""}`}
          >
            Plan funding
          </Link>
        }
      >
        Look at the underlying records together. Different periods and missing
        fields limit comparability.
      </Header>
      <State data={data} error={error}>
        {data && (
          <Panel variant="open">
            <div
              className="table-wrap"
              role="region"
              aria-label="Organization comparison"
              tabIndex={0}
            >
              <table className="comparison-table">
                <thead>
                  <tr>
                    <th>Reported measure</th>
                    {data.organizations.map((o: Row) => (
                      <th key={o.id}>
                        <Link href={`/organizations/${o.id}`}>{o.name}</Link>
                        <Badge>{o.source_kind}</Badge>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {[
                    ["Fiscal period", "tax_year"],
                    ["Revenue (USD)", "revenue"],
                    ["Expenses (USD)", "expenses"],
                    ["Program expenses (USD)", "program_expenses"],
                    ["Assets (USD)", "assets"],
                    ["Liabilities (USD)", "liabilities"],
                  ].map(([caption, key]) => (
                    <tr key={key}>
                      <th scope="row">{caption}</th>
                      {data.organizations.map((o: Row) => (
                        <td key={o.id} className="numeric">
                          {key === "tax_year"
                            ? o.latest_filing?.[key] || "Unknown"
                            : money(o.latest_filing?.[key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                  <tr>
                    <th>Reported service areas</th>
                    {data.organizations.map((o: Row) => (
                      <td key={o.id}>
                        {o.service_areas.map((g: Row) => g.name).join(", ") ||
                          "Unknown"}
                      </td>
                    ))}
                  </tr>
                  <tr>
                    <th>Approved capacity</th>
                    {data.organizations.map((o: Row) => (
                      <td key={o.id}>
                        {money(o.capacity_cents, true)}
                        <small>{o.capacity_note}</small>
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </div>
            {data.caveats.map((c: string) => (
              <Notice key={c}>{c}</Notice>
            ))}
          </Panel>
        )}
      </State>
    </>
  );
}
export function Allocation() {
  const q = useSearchParams(),
    router = useRouter();
  const { data, error } = useResource<OrganizationRecord[]>("organizations/");
  const [ids, setIds] = useState(
    (q.get("ids") || "").split(",").filter(Boolean),
  );
  return (
    <>
      <Header eyebrow="Funding plan draft" title="Plan funding">
        Choose candidates, disclose planning assumptions, then review the
        server-calculated allocation.
      </Header>
      <Notice>
        This constrained, proportional planning heuristic does not estimate
        marginal impact. No money is moved. Unknown capacity requires an
        explicit assumption; otherwise funds remain unallocated.
      </Notice>
      <State data={data} error={error}>
        <Form
          className="form allocation-form"
          submit="Calculate & save draft"
          success="Draft saved."
          onSubmit={async (f) => {
            const draft = await mutate("portfolios/", "POST", {
              name: text(f, "name"),
              budget_cents: toCents(text(f, "budget")),
              currency: "USD",
              constraints: {
                objective: "Donor-selected proportional planning weights",
              },
              candidates: ids.map((id) => ({
                organization_id: id,
                weight: text(f, `weight_${id}`) || "1",
                ...(text(f, `cap_${id}`)
                  ? { cap_cents: toCents(text(f, `cap_${id}`)) }
                  : {}),
                assumption_note: text(f, `note_${id}`),
                dimensions: Object.fromEntries(
                  ["need", "evidence", "financial_uncertainty", "goal_fit"].map(
                    (key) => [key, text(f, `${key}_${id}`) || null],
                  ),
                ),
                excluded: f.has(`exclude_${id}`),
                minimum_cents: toCents(text(f, `minimum_${id}`) || "0"),
              })),
            });
            router.push(`/portfolios/${draft.id}`);
          }}
        >
          <Panel title="Plan details" variant="open">
            <div className="form-grid">
              <Field
                label="Portfolio name"
                name="name"
                value="Food security funding plan"
                required
              />
              <Field
                label="Total budget (USD)"
                name="budget"
                value="25000.00"
                inputMode="decimal"
                required
              />
            </div>
          </Panel>
          <Panel title="Candidates and constraints" variant="open">
            <Field label="Add an organization" name="candidate">
              <select
                value=""
                onChange={(e) => setIds([...ids, e.target.value])}
              >
                <option value="">Choose an organization</option>
                {data
                  ?.filter((o) => !ids.includes(o.id))
                  .map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.name}
                    </option>
                  ))}
              </select>
            </Field>
            {!ids.length && <Empty title="Choose candidates to begin" />}
            {ids.map((id) => {
              const o = data?.find((o) => o.id === id);
              return (
                <div className="candidate" key={id}>
                  <div className="panel-heading">
                    <h3>{o?.name}</h3>
                    <button
                      type="button"
                      className="text-button"
                      onClick={() => setIds(ids.filter((x) => x !== id))}
                    >
                      Remove
                    </button>
                  </div>
                  <p className="fine">
                    Recorded capacity: {money(o?.capacity_cents, true)} ·{" "}
                    {o?.capacity_note ||
                      "No independent capacity confirmation."}
                  </p>
                  <div className="form-grid">
                    <Field
                      label="Planning weight"
                      name={`weight_${id}`}
                      value="1"
                      type="number"
                      min="0"
                      step="0.1"
                      hint="Your disclosed priority; not an impact score."
                    />
                    <Field
                      label="Maximum allocation (USD)"
                      name={`cap_${id}`}
                      value={
                        o?.capacity_cents != null
                          ? dollars(o.capacity_cents)
                          : ""
                      }
                      inputMode="decimal"
                    />
                    <Field
                      label="Minimum allocation (USD)"
                      name={`minimum_${id}`}
                      value="0.00"
                      inputMode="decimal"
                    />
                    <Field
                      label="Capacity assumption"
                      name={`note_${id}`}
                      hint="Required when entering a cap for unknown capacity."
                    />
                  </div>
                  <details>
                    <summary>
                      Separate planning dimensions and limitations
                    </summary>
                    <p className="fine">
                      Keep need, evidence, financial uncertainty and goal fit
                      separate. Blank notes remain unknown and are not converted
                      into scores. The weight above is your explicit planning
                      assumption.
                    </p>
                    <div className="form-grid">
                      {[
                        "need",
                        "evidence",
                        "financial_uncertainty",
                        "goal_fit",
                      ].map((key) => (
                        <Field
                          key={key}
                          label={`${label(key)} rationale`}
                          name={`${key}_${id}`}
                          maxLength={1000}
                          placeholder="Unknown / not yet assessed"
                        />
                      ))}
                    </div>
                  </details>
                  <label className="check-label">
                    <input type="checkbox" name={`exclude_${id}`} /> Exclude
                    from this draft
                  </label>
                </div>
              );
            })}
          </Panel>
        </Form>
      </State>
    </>
  );
}
export function Portfolios() {
  const { data, error } = useResource<Row[]>("portfolios/");
  return (
    <>
      <Header
        title="Funding plans"
        action={
          <Link className="button primary" href="/allocate">
            Create funding plan
          </Link>
        }
      >
        Saved drafts, source snapshots, and reviewed planning decisions.
      </Header>
      <State data={data} error={error}>
        {data?.length ? (
          <Panel>
            <div
              className="table-wrap"
              role="region"
              aria-label="Saved funding plans"
              tabIndex={0}
            >
              <table>
                <thead>
                  <tr>
                    <th>Funding plan</th>
                    <th>Budget</th>
                    <th>Unallocated</th>
                    <th>Review status</th>
                    <th>Revision</th>
                  </tr>
                </thead>
                <tbody>
                  {data.map((p) => (
                    <tr key={p.id}>
                      <td>
                        <Link href={`/portfolios/${p.id}`}>{p.title}</Link>
                        <small>{date(p.created_at)}</small>
                      </td>
                      <td className="numeric">
                        {money(p.portfolio.budget_cents, true)}
                      </td>
                      <td className="numeric">
                        {money(p.portfolio.unallocated_cents, true)}
                      </td>
                      <td>
                        <Badge>{p.status}</Badge>
                      </td>
                      <td>{p.revision}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Panel>
        ) : (
          <Empty title="Your first funding plan starts here">
            Choose organizations in discovery, then create a draft to save your
            assumptions and allocations.
          </Empty>
        )}
      </State>
    </>
  );
}
function PortfolioCoverage({ data }: { data: Row }) {
  return (
    <Panel title="Current geographic coverage" variant="open">
      <p>{data.scope}</p>
      <Notice>{data.caveat}</Notice>
      <div
        className="table-wrap"
        role="region"
        aria-label="Current geographic coverage"
        tabIndex={0}
      >
        <table>
          <caption>
            Reported service areas and possible investigation gaps
          </caption>
          <thead>
            <tr>
              <th>Area / type</th>
              <th>Planned organizations</th>
              <th>Interpretation</th>
              <th>Sources</th>
            </tr>
          </thead>
          <tbody>
            {data.areas.map((area: Row) => (
              <tr key={area.code}>
                <td>
                  {area.name}
                  <small>
                    {area.code} · {label(area.kind)}
                  </small>
                </td>
                <td>
                  {area.selected_organizations.length
                    ? area.selected_organizations.map((org: Row) => (
                        <p key={org.id}>
                          <Link href={`/organizations/${org.id}`}>
                            {org.name}
                          </Link>{" "}
                          · {label(org.basis)}
                        </p>
                      ))
                    : "None in this plan"}
                </td>
                <td>
                  {label(area.status)}
                  <small>
                    {area.directory_organization_count} organizations report
                    this area in the available directory.
                  </small>
                </td>
                <td>
                  {area.source_ids.map((source: string, i: number) => (
                    <p key={source}>
                      <Link href={`/sources/${source}`}>Source {i + 1}</Link>
                    </p>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {!data.areas.length && (
        <Empty title="No eligible service-area records">
          Geographic coverage is unknown; headquarters locations are not
          substituted.
        </Empty>
      )}
      {!!data.unknown_service_area_organizations.length && (
        <Notice>
          Service areas unknown for:{" "}
          {data.unknown_service_area_organizations
            .map((org: Row) => org.name)
            .join(", ")}
          . Collect reported service geography before judging coverage.
        </Notice>
      )}
      <details>
        <summary>Coverage method and current source revisions</summary>
        <Details
          data={{
            method_version: data.method_version,
            as_of: data.as_of,
            sources: data.sources,
          }}
        />
      </details>
    </Panel>
  );
}
export function Portfolio({ id }: { id: string }) {
  const [version, setVersion] = useState(0);
  const { data, error } = useResource(`portfolios/${id}/`, version);
  const ws = useWorkspace();
  const write = ["owner", "administrator", "analyst"].includes(ws.role);
  return (
    <State data={data} error={error}>
      {data && (
        <>
          <Header
            eyebrow="Saved funding plan · No money moves"
            title={data.title}
            action={
              <div className="actions">
                <ExportButton id={id} />
                <Link className="button secondary" href={`/reports/${id}`}>
                  Printable report ↗
                </Link>
              </div>
            }
          >
            Revision {data.revision} · {data.method_version} ·{" "}
            <Badge>{data.status}</Badge>
          </Header>
          <div className="summary-strip">
            <div>
              <small>Total budget</small>
              <strong>{money(data.portfolio.budget_cents, true)}</strong>
            </div>
            <div>
              <small>Unallocated funds</small>
              <strong>{money(data.portfolio.unallocated_cents, true)}</strong>
            </div>
            <div>
              <small>Review</small>
              <strong>{label(data.status)}</strong>
            </div>
          </div>
          <Notice>
            Allocations are a planning draft until separately approved. Editing
            a plan invalidates approval. Program spending and donor weights are
            not impact estimates.
          </Notice>
          <Panel title="Allocation and rationale" variant="open">
            <Form
              submit="Save allocation edits"
              onSubmit={async (f) => {
                await mutate(`portfolios/${id}/`, "PATCH", {
                  revision: data.revision,
                  allocations: data.portfolio.allocations.map((a: Row) => ({
                    organization_id: a.organization_id,
                    amount_cents: toCents(text(f, a.organization_id)),
                  })),
                });
                setVersion(version + 1);
              }}
            >
              <div
                className="table-wrap"
                role="region"
                aria-label="Allocation amounts and rationale"
                tabIndex={0}
              >
                <table>
                  <thead>
                    <tr>
                      <th>Organization</th>
                      <th>Planning amount (USD)</th>
                      <th>Cap</th>
                      <th>Rationale</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.portfolio.allocations.map((a: Row) => (
                      <tr key={a.id}>
                        <td>
                          <Link href={`/organizations/${a.organization_id}`}>
                            {a.organization_name}
                          </Link>
                        </td>
                        <td>
                          <input
                            aria-label={`Allocation for ${a.organization_name}`}
                            name={a.organization_id}
                            defaultValue={dollars(a.amount_cents)}
                            readOnly={!write}
                            inputMode="decimal"
                          />
                        </td>
                        <td>{money(a.cap_cents, true)}</td>
                        <td>{a.explanation}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Form>
            <details className="source-drawer">
              <summary>Method & constraint results</summary>
              <Details data={data.payload} />
            </details>
          </Panel>
          {data.portfolio.geographic_coverage && (
            <PortfolioCoverage data={data.portfolio.geographic_coverage} />
          )}
          {write && (
            <ReviewSubmit
              artifact={data}
              onSaved={() => setVersion(version + 1)}
            />
          )}
          <Attributions artifact={data} />
          <Sources sources={data.sources} />
          {data.review && (
            <Panel title="Review decision">
              <Details data={data.review} />
            </Panel>
          )}
        </>
      )}
    </State>
  );
}
