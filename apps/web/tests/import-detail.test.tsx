import { afterEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { ImportDetail } from "../components/ngo";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
vi.mock("../components/application", () => ({
  useWorkspace: () => ({ id: "workspace", role: "owner", kind: "ngo" }),
}));
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe("Worker import status", () => {
  it("keeps polling through processing and reveals mapping when the worker finishes", async () => {
    vi.useFakeTimers();
    const response = (status: string) => ({
      ok: true,
      json: async () => ({
        data: {
          filename: "aggregate.csv",
          status,
          columns: ["program_name"],
          mapping: {},
          preview: [],
          diagnostics: [],
        },
      }),
    });
    const fetch = vi
      .fn()
      .mockResolvedValueOnce(response("queued"))
      .mockResolvedValueOnce(response("processing"))
      .mockResolvedValueOnce(response("needs_mapping"));
    vi.stubGlobal("fetch", fetch);
    await act(async () => {
      render(<ImportDetail id="import-one" />);
    });
    expect(screen.getByText("Queued", { exact: true })).toBeVisible();
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.getByText("Processing", { exact: true })).toBeVisible();
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(
      screen.getByRole("button", { name: "Validate mapping" }),
    ).toBeVisible();
    expect(screen.getByLabelText("program_name")).toHaveValue("program_name");
    await act(async () => {
      vi.advanceTimersByTime(9000);
    });
    expect(fetch).toHaveBeenCalledTimes(3);
  });
});
