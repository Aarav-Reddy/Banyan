import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { Discovery } from "../components/donor";
import { Details, PrintSupport, Sources } from "../components/ui";
import {
  PortfolioReportContent,
  PortfolioReviewContent,
  TechnicalDetails,
} from "../components/report-content";

const navigation = vi.hoisted(() => ({ query: "", push: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: navigation.push }),
  useSearchParams: () => new URLSearchParams(navigation.query),
}));
vi.mock("../components/application", () => ({
  useWorkspace: () => ({ id: "workspace", role: "owner", kind: "foundation" }),
}));
afterEach(() => {
  navigation.query = "";
  navigation.push.mockReset();
  vi.unstubAllGlobals();
});
function discovery() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => ({
      ok: true,
      json: async () => ({
        data: url.includes("geographies/")
          ? [{ code: "US-MD-Baltimore", name: "Baltimore", kind: "city" }]
          : [],
      }),
    })),
  );
  return render(<Discovery />);
}

describe("Discovery presentation preserves filter transport", () => {
  it("keeps every advanced control mounted and submits its exact value while closed", async () => {
    discovery();
    await screen.findByRole("option", { name: "Baltimore (city)" });
    const disclosure = screen.getByText("More filters").closest("details")!;
    disclosure.open = true;
    for (const [caption, value] of [
      ["Organization", "Synthetic test"],
      ["Cause", "food_security"],
      ["Service area", "US-MD-Baltimore"],
      ["Population", "households"],
      ["Annual revenue", "small"],
      ["Planning budget (USD)", "100.01"],
      ["Financial preference", "capacity_building"],
      ["Desired outcome code", "food_security_improved"],
      ["Maximum follow-up (days)", "180"],
    ]) {
      fireEvent.change(screen.getByLabelText(caption, { exact: true }), {
        target: { value },
      });
    }
    expect(screen.getByText("6 additional filters set")).toBeInTheDocument();
    disclosure.open = false;
    expect(screen.getByLabelText("Population")).toHaveValue("households");
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await waitFor(() => expect(navigation.push).toHaveBeenCalledOnce());
    const query = new URL(navigation.push.mock.calls[0][0], "http://local")
      .searchParams;
    expect(Object.fromEntries(query)).toEqual({
      q: "Synthetic test",
      cause: "food_security",
      location: "US-MD-Baltimore",
      population: "households",
      size: "small",
      risk: "capacity_building",
      outcome_definition: "food_security_improved",
      horizon_days: "180",
      budget_cents: "10001",
    });
  });
  it("indicates existing advanced query values without changing defaults", async () => {
    navigation.query = "population=households&budget_cents=29&risk=all";
    discovery();
    await screen.findByText("No organizations match these filters");
    expect(screen.getByText("2 additional filters set")).toBeVisible();
    expect(screen.getByLabelText("Planning budget (USD)")).toHaveValue("0.29");
    expect(screen.getByLabelText("Financial preference")).toHaveValue("all");
    expect(
      screen.getByText("More filters").closest("details"),
    ).not.toHaveAttribute("open");
  });
  it("opens an invalid money field, preserves values, and does not navigate", async () => {
    discovery();
    await screen.findByText("No organizations match these filters");
    fireEvent.change(screen.getByLabelText("Organization", { exact: true }), {
      target: { value: "Keep this search" },
    });
    fireEvent.change(screen.getByLabelText("Planning budget (USD)"), {
      target: { value: "0.001" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Apply filters" }));
    await screen.findByRole("alert");
    expect(navigation.push).not.toHaveBeenCalled();
    expect(screen.getByText("More filters").closest("details")).toHaveAttribute(
      "open",
    );
    expect(screen.getByLabelText("Planning budget (USD)")).toHaveFocus();
    expect(screen.getByLabelText("Planning budget (USD)")).toHaveValue("0.001");
    expect(screen.getByLabelText("Organization", { exact: true })).toHaveValue(
      "Keep this search",
    );
  });
});

describe("Complete report data and print disclosures", () => {
  it("keeps manually edited review context visible without inventing allocation rows", () => {
    render(
      <PortfolioReviewContent
        payload={{
          manual_edit: true,
          unallocated_cents: 1,
          method_version: "manual-v1",
        }}
      />,
    );
    expect(screen.getByText(/This plan was manually edited/)).toBeVisible();
    expect(screen.getByText("Manual edit")).toBeVisible();
    expect(screen.getByText("Yes", { exact: true })).toBeVisible();
    expect(screen.getByText("1", { exact: true })).toBeVisible();
    expect(screen.getByText("manual-v1", { exact: true })).toBeVisible();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText("Planning budget")).not.toBeInTheDocument();
  });
  it("retains unknown nested fields and distinct missing, empty, false and zero values inertly", () => {
    render(
      <Details
        data={{
          missing: null,
          unavailable_measure: undefined,
          empty: "",
          false_value: false,
          zero: 0,
          array: [],
          object: {},
          unknown_payload: { unusual_key: "<script>alert(1)</script>" },
        }}
      />,
    );
    for (const value of [
      "Not reported",
      "Unavailable",
      "Empty text",
      "No",
      "0",
      "No items reported (empty list)",
      "No fields reported (empty object)",
      "<script>alert(1)</script>",
    ])
      expect(screen.getByText(value, { exact: true })).toBeInTheDocument();
    expect(document.querySelector("script")).toBeNull();
    expect(screen.getByText("Unusual key")).toHaveAttribute(
      "title",
      "unusual_key",
    );
  });
  it("prints closed source and technical disclosures then restores their original state", () => {
    render(
      <main>
        <PrintSupport />
        <details open>
          <summary>Already open</summary>
          <p>Visible context</p>
        </details>
        <TechnicalDetails
          data={{ unknown_original_field: "Keep this payload" }}
        />
        <Sources
          sources={[
            {
              id: "source",
              title: "Synthetic source",
              kind: "synthetic_demo",
              revision: 1,
              checksum: "checksum",
              source_url: "https://example.invalid/source",
            },
          ]}
        />
      </main>,
    );
    const details = Array.from(
      document.querySelectorAll<HTMLDetailsElement>("main details"),
    );
    expect(details.map((d) => d.open)).toEqual([true, false, false]);
    fireEvent(window, new Event("beforeprint"));
    expect(details.every((d) => d.open)).toBe(true);
    expect(screen.getByText("Keep this payload")).toBeVisible();
    expect(
      screen.getByRole("link", { name: "Synthetic source" }),
    ).toHaveAttribute("href", "/sources/source");
    expect(
      screen.getByRole("link", { name: /Open original source/ }),
    ).toHaveAttribute("href", "https://example.invalid/source");
    fireEvent(window, new Event("afterprint"));
    expect(details.map((d) => d.open)).toEqual([true, false, false]);
  });
  it("places actual allocations before detailed planning constraints without recalculation", () => {
    render(
      <PortfolioReportContent
        data={{
          method_version: "pilot-v1",
          portfolio: {
            budget_cents: 10001,
            unallocated_cents: 1,
            currency: "USD",
            allocations: [
              {
                id: "a",
                organization_name: "Synthetic organization",
                amount_cents: 10000,
                explanation: "Reported rationale",
              },
            ],
            constraints: { unknown_constraint: false },
          },
        }}
      />,
    );
    expect(screen.getByText("$100.01")).toBeVisible();
    expect(screen.getByText("$0.01")).toBeVisible();
    expect(screen.getByRole("cell", { name: "$100.00" })).toBeVisible();
    const table = screen.getByRole("table");
    const constraints = screen.getByText(
      "View all planning inputs and candidate constraints",
    );
    expect(
      table.compareDocumentPosition(constraints) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    fireEvent.click(constraints);
    expect(screen.getByText("Unknown constraint")).toBeInTheDocument();
    expect(screen.getByText("No", { exact: true })).toBeInTheDocument();
  });
});
