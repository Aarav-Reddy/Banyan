import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import {
  Attributions,
  CommunityContext,
  Benchmark,
  PasswordReset,
  ContactConsent,
} from "../components/pilot";

vi.mock("next/navigation", () => ({
  useSearchParams: () =>
    new URLSearchParams("uid=encoded-user&token=single-use-token"),
}));
vi.mock("../components/application", () => ({
  useWorkspace: () => ({ id: "workspace", kind: "ngo", role: "owner" }),
}));
afterEach(() => vi.unstubAllGlobals());
const response = (data: unknown) => ({
  ok: true,
  json: async () => ({ data }),
});

describe("Pilot evidence boundaries", () => {
  it("keeps required attribution visible, linked, and inert", () => {
    render(
      <Attributions
        artifact={{
          attributions: [
            {
              source_id: "source-one",
              text: "<script>untrusted contributor</script>",
            },
          ],
        }}
      />,
    );
    expect(
      screen.getByText("<script>untrusted contributor</script>"),
    ).toBeVisible();
    expect(screen.getByRole("link", { name: "Source record" })).toHaveAttribute(
      "href",
      "/sources/source-one",
    );
    expect(document.querySelector("script")).toBeNull();
  });
  it("renders public context separately and never supplies missing estimates", () => {
    render(
      <CommunityContext
        geographies={[
          {
            code: "city",
            context: {
              source_kind: "public_source",
              geography_name: "City-wide census context",
              period_start: "2020-01-01",
              period_end: "2024-12-31",
              indicators: [{ label: "Income", estimate: null, unit: "USD" }],
              caveat: "Not a ZIP or food insecurity measurement.",
              source_url: "javascript:alert(1)",
            },
          },
          {
            code: "synthetic",
            context: {
              source_kind: "synthetic_demo",
              indicators: [{ label: "Invented statistic", estimate: "123" }],
            },
          },
        ]}
      />,
    );
    expect(screen.getByText("Not reported")).toBeVisible();
    expect(
      screen.getByText("Not a ZIP or food insecurity measurement."),
    ).toBeVisible();
    expect(screen.queryByText("Invented statistic")).not.toBeInTheDocument();
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
  it("does not render numerical cells for a suppressed benchmark", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        response({
          status: "suppressed",
          reason: "At least three compatible peers required",
          median: "0.812345",
          target_value: "0.923456",
        }),
      ),
    );
    render(<Benchmark />);
    expect(
      await screen.findByText("At least three compatible peers required"),
    ).toBeVisible();
    expect(screen.queryByText("0.812345")).not.toBeInTheDocument();
    expect(screen.queryByText("0.923456")).not.toBeInTheDocument();
  });
});

describe("Account recovery and explicit consent", () => {
  it("rejects mismatched passwords locally and preserves the entered password", async () => {
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    render(<PasswordReset />);
    fireEvent.change(screen.getByLabelText("New password"), {
      target: { value: "A-long-new-password!" },
    });
    fireEvent.change(screen.getByLabelText("Confirm new password"), {
      target: { value: "Different-password!" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Update password" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "passwords do not match",
    );
    expect(fetcher).not.toHaveBeenCalled();
    expect(screen.getByLabelText("New password")).toHaveValue(
      "A-long-new-password!",
    );
  });
  it("sends an explicit false value when withdrawing optional contact consent", async () => {
    const fetcher = vi.fn().mockResolvedValue(
      response({
        name: "Contact Person",
        email: "contact@example.test",
        enabled: true,
        revision: 3,
      }),
    );
    vi.stubGlobal("fetch", fetcher);
    render(<ContactConsent />);
    const checkbox = await screen.findByRole("checkbox");
    expect(checkbox).toBeChecked();
    fireEvent.click(checkbox);
    fireEvent.click(
      screen.getByRole("button", { name: "Save contact consent" }),
    );
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([, init]) => init?.method === "PUT"),
      ).toBe(true),
    );
    const [, options] = fetcher.mock.calls.find(
      ([, init]) => init?.method === "PUT",
    )!;
    expect(JSON.parse(options.body)).toEqual({
      name: "Contact Person",
      email: "contact@example.test",
      enabled: false,
      revision: 3,
    });
  });
});
