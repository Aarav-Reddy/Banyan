import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Reviews } from "../components/shared";
vi.mock("../components/application", () => ({
  useWorkspace: () => ({ id: "reviewer-workspace", role: "reviewer" }),
}));
vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));
afterEach(() => vi.unstubAllGlobals());

describe("Version-bound approval withdrawal", () => {
  it("loads approved assignments and submits only withdrawal of the displayed revision", async () => {
    const fetcher = vi.fn(async (url: string, options?: RequestInit) => ({
      ok: true,
      json: async () => ({
        data: url.endsWith("?status=approved")
          ? [
              {
                id: "artifact-id",
                revision: 7,
                title: "Approved source concern",
                kind: "source_issue",
                cause: "food_security",
                geography: "Baltimore",
                sources: [],
                payload: { issue: "Reporting period disputed" },
              },
            ]
          : options?.method === "POST"
            ? { saved: true }
            : [],
      }),
    }));
    vi.stubGlobal("fetch", fetcher);
    render(<Reviews />);
    expect(
      await screen.findByText("No assigned reviews pending"),
    ).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Approved" }));
    expect(await screen.findByText("Approved source concern")).toBeVisible();
    expect(screen.getAllByRole("option")).toHaveLength(1);
    expect(screen.getByRole("option")).toHaveValue("withdrawn");
    const reason = screen.getByLabelText("Reason, scope & caveats");
    expect(reason).toBeRequired();
    fireEvent.change(reason, {
      target: { value: "New evidence invalidates the approved period." },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Withdraw approved revision" }),
    );
    await waitFor(() =>
      expect(
        fetcher.mock.calls.some(([, init]) => init?.method === "POST"),
      ).toBe(true),
    );
    const [, options] = fetcher.mock.calls.find(
      ([, init]) => init?.method === "POST",
    )!;
    expect(JSON.parse(options?.body as string)).toEqual({
      revision: 7,
      decision: "withdrawn",
      reason: "New evidence invalidates the approved period.",
    });
  });
});
