"use client";
import Link from "next/link";
import type { ReactNode } from "react";
import { Row, date, money } from "@/lib/api";
import { Badge, Details, Empty, Panel } from "./ui";

/** Formatting only: missing, empty and false values must not become zero. */
function Value({ value }: { value: unknown }) {
  if (value === null) return <>Not reported</>;
  if (value === undefined) return <>Unavailable</>;
  if (value === "") return <>Empty</>;
  if (typeof value === "boolean") return <>{value ? "Yes" : "No"}</>;
  if (typeof value === "object") return <Details data={{ value }} />;
  return <>{String(value)}</>;
}

function SourceLink({ id, locator }: { id: unknown; locator?: unknown }) {
  return id ? (
    <>
      <Link href={`/sources/${id}`}>Source record</Link>
      {locator !== undefined && (
        <p>
          <Value value={locator} />
        </p>
      )}
    </>
  ) : (
    <Value value={id} />
  );
}

export function TechnicalDetails({
  data,
  title = "Complete report data and technical details",
}: {
  data: Row;
  title?: string;
}) {
  return (
    <details className="source-drawer report-technical">
      <summary>{title}</summary>
      <Details data={data} />
    </details>
  );
}

export function PortfolioReportContent({ data }: { data: Row }) {
  const p = data.portfolio;
  return (
    <>
      <Panel title="Funding allocation" variant="open">
        <dl className="record-metadata report-summary">
          <div>
            <dt>Planning budget</dt>
            <dd>{money(p.budget_cents, true)}</dd>
          </div>
          <div>
            <dt>Unallocated</dt>
            <dd>{money(p.unallocated_cents, true)}</dd>
          </div>
          <div>
            <dt>Currency</dt>
            <dd>
              <Value value={p.currency} />
            </dd>
          </div>
        </dl>
        <div
          className="table-wrap"
          role="region"
          aria-label="Funding allocation table"
          tabIndex={0}
        >
          <table className="report-table">
            <thead>
              <tr>
                <th scope="col">Organization</th>
                <th scope="col">Amount</th>
                <th scope="col">Allocation rationale</th>
              </tr>
            </thead>
            <tbody>
              {p.allocations.map((a: Row) => (
                <tr key={a.id}>
                  <th scope="row">{a.organization_name}</th>
                  <td className="numeric">{money(a.amount_cents, true)}</td>
                  <td>
                    <Value value={a.explanation} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted">
          Planning amounts only. This report does not transfer money.
        </p>
      </Panel>
      <Panel title="Planning method and constraints" variant="open">
        <p>
          Method version: <Value value={data.method_version} />
        </p>
        <TechnicalDetails
          data={{ planning_inputs: p.constraints }}
          title="View all planning inputs and candidate constraints"
        />
      </Panel>
    </>
  );
}

/** Review assignments supply the allocation payload, not organization names. */
export function PortfolioReviewContent({ payload: p }: { payload: Row }) {
  if (!Array.isArray(p.allocations) || p.budget_cents == null)
    return (
      <>
        <p>
          {p.manual_edit === true
            ? "This plan was manually edited. "
            : "This review record contains supporting details. "}
          Open the complete artifact to inspect its current allocation rows.
        </p>
        <Details data={p} />
      </>
    );
  return (
    <>
      <dl className="record-metadata report-summary">
        <div>
          <dt>Planning budget</dt>
          <dd>{money(p.budget_cents, true)}</dd>
        </div>
        <div>
          <dt>Unallocated</dt>
          <dd>{money(p.unallocated_cents, true)}</dd>
        </div>
      </dl>
      <p>
        <Value value={p.objective} />
      </p>
      <div
        className="table-wrap"
        role="region"
        aria-label="Proposed allocations for review"
        tabIndex={0}
      >
        <table className="report-table">
          <thead>
            <tr>
              <th scope="col">Candidate identifier</th>
              <th scope="col">Amount</th>
              <th scope="col">Capacity and assumptions</th>
              <th scope="col">Rationale</th>
            </tr>
          </thead>
          <tbody>
            {p.allocations?.map((a: Row) => (
              <tr key={a.id}>
                <th scope="row">
                  <Value value={a.id} />
                </th>
                <td className="numeric">{money(a.amount_cents, true)}</td>
                <td>
                  <p>Cap: {money(a.cap_cents, true)}</p>
                  <Details
                    data={{
                      capacity_basis: a.capacity_basis,
                      assumption_note: a.assumption_note,
                    }}
                  />
                </td>
                <td>
                  <Value value={a.explanation} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Details data={{ limitations: p.limitations }} />
      <TechnicalDetails
        data={p}
        title="Complete allocation inputs and source identifiers"
      />
    </>
  );
}

export function ImpactReportContent({
  data,
  attribution,
}: {
  data: Row;
  attribution: (record: Row) => ReactNode;
}) {
  const programName = (id: unknown) =>
    data.programs.find((p: Row) => p.id === id)?.name ?? id;
  return (
    <>
      <Panel title="Programs" variant="open">
        {data.programs.length ? (
          data.programs.map((p: Row) => (
            <article className="report-record" key={p.id}>
              <h3>
                <Value value={p.name} />
              </h3>
              <Details
                data={{
                  cause: p.cause,
                  intervention: p.intervention,
                  population: p.population,
                  geography: p.geography,
                  context: p.context,
                }}
              />
              <SourceLink id={p.source_id} />
              {attribution(p)}
            </article>
          ))
        ) : (
          <Empty title="No programs reported" />
        )}
      </Panel>
      <Panel title="Source-reported outcomes" variant="open">
        {data.observations.length ? (
          <div
            className="table-wrap"
            role="region"
            aria-label="Source-reported outcomes table"
            tabIndex={0}
          >
            <table className="report-table">
              <thead>
                <tr>
                  <th scope="col">Program and outcome</th>
                  <th scope="col">Reported values</th>
                  <th scope="col">Period and design</th>
                  <th scope="col">Uncertainty and gaps</th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                {data.observations.map((o: Row) => (
                  <tr key={o.id}>
                    <th scope="row">
                      <Value value={programName(o.program_id)} />
                      <p>
                        <Value value={o.outcome_definition} />
                      </p>
                    </th>
                    <td>
                      <Details
                        data={{
                          numerator: o.numerator,
                          denominator: o.denominator,
                          unit: o.unit,
                          direction: o.direction,
                        }}
                      />
                    </td>
                    <td>
                      <p>
                        {date(o.period_start)} – {date(o.period_end)}
                      </p>
                      <Details
                        data={{
                          followup_months: o.followup_months,
                          study_design: o.study_design,
                          comparator: o.comparator,
                        }}
                      />
                    </td>
                    <td>
                      <Details
                        data={{
                          uncertainty: o.uncertainty,
                          missingness: o.missingness,
                        }}
                      />
                      {attribution(o)}
                    </td>
                    <td>
                      <SourceLink id={o.source_id} locator={o.locator} />
                      <Badge>{o.source_kind}</Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No outcomes reported" />
        )}
      </Panel>
      <Panel title="Reported costs" variant="open">
        <p className="muted">
          Amounts retain their reported currency, unit and period. Different
          bases must not be combined.
        </p>
        {data.costs.length ? (
          <div
            className="table-wrap"
            role="region"
            aria-label="Reported costs table"
            tabIndex={0}
          >
            <table className="report-table">
              <thead>
                <tr>
                  <th scope="col">Program</th>
                  <th scope="col">Amount and currency</th>
                  <th scope="col">Reporting basis</th>
                  <th scope="col">Period</th>
                  <th scope="col">Source</th>
                </tr>
              </thead>
              <tbody>
                {data.costs.map((c: Row) => (
                  <tr key={c.id}>
                    <th scope="row">
                      <Value value={programName(c.program_id)} />
                    </th>
                    <td className="numeric">
                      <Value value={c.amount} /> <Value value={c.currency} />
                    </td>
                    <td>
                      <Details
                        data={{ unit: c.unit, denominator: c.denominator }}
                      />
                    </td>
                    <td>
                      {date(c.period_start)} – {date(c.period_end)}
                    </td>
                    <td>
                      <SourceLink id={c.source_id} />
                      <Badge>{c.source_kind}</Badge>
                      {attribution(c)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <Empty title="No costs reported" />
        )}
      </Panel>
      <Panel title="Intervention evidence" variant="open">
        {data.cards.length ? (
          data.cards.map((c: Row) => (
            <article className="report-record" key={c.id}>
              <h3>
                <Link href={`/evidence/${c.id}`}>{c.title}</Link>
              </h3>
              <dl className="record-metadata">
                <div>
                  <dt>Evidence type</dt>
                  <dd>
                    <Value value={c.evidence_label} />
                  </dd>
                </div>
                <div>
                  <dt>Editorial review</dt>
                  <dd>
                    <Badge>{c.status}</Badge> · Revision{" "}
                    <Value value={c.revision} />
                  </dd>
                </div>
              </dl>
              <Details data={{ failures: c.failures, caveats: c.caveats }} />
              <div className="actions">
                {c.source_ids.map((sourceId: string) => (
                  <Link href={`/sources/${sourceId}`} key={sourceId}>
                    Source {sourceId}
                  </Link>
                ))}
              </div>
              {attribution(c)}
            </article>
          ))
        ) : (
          <Empty title="No intervention evidence reported" />
        )}
      </Panel>
      <Panel title="Data quality gaps" variant="open">
        {data.data_quality.length ? (
          <ul className="checklist">
            {data.data_quality.map((q: Row, i: number) => (
              <li key={i}>
                <Value value={q.issue} />
                <p className="muted">
                  Observation <Value value={q.observation_id} />
                </p>
                {attribution(q)}
              </li>
            ))}
          </ul>
        ) : (
          <Empty title="No data quality gaps reported" />
        )}
      </Panel>
    </>
  );
}
