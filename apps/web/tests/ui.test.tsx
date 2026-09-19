import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { Form, Field, Notice, Details, Sources } from "../components/ui";
import { toCents, dollars, configureSession, api } from "../lib/api";
describe("Accessible forms and truthful evidence", () => {
  it("preserves user-entered data and announces a failed server save", async () => {
    const submit = vi
      .fn()
      .mockRejectedValue(
        new Error("Revision changed; inspect the new source."),
      );
    render(
      <Form onSubmit={submit}>
        <Field label="Program name" name="name" required />
      </Form>,
    );
    fireEvent.change(screen.getByLabelText("Program name"), {
      target: { value: "Community kitchen" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Save changes" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Revision changed",
    );
    expect(screen.getByLabelText("Program name")).toHaveValue(
      "Community kitchen",
    );
    expect(screen.queryByText("Saved.")).not.toBeInTheDocument();
  });
  it("does not turn missing measures into zero", () => {
    render(<Details data={{ revenue: null, expenses: 0 }} />);
    expect(screen.getByText("Not reported")).toBeInTheDocument();
    expect(screen.getByText("0")).toBeInTheDocument();
  });
  it("rejects unsafe original source schemes", () => {
    render(
      <Sources
        sources={[
          {
            id: "1",
            title: "Uploaded note",
            kind: "ngo_contributed",
            source_url: "javascript:alert(1)",
            revision: 1,
            checksum: "abc",
          },
        ]}
      />,
    );
    expect(screen.queryByText(/Open original source/)).not.toBeInTheDocument();
  });
  it("uses non-color text for permission failures", () => {
    render(<Notice tone="error">Source access withdrawn</Notice>);
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Source access withdrawn",
    );
  });
});
describe("Exact transport amounts and authenticated API", () => {
  it("converts decimal input into exact safe integer cents", () => {
    expect(toCents("0.29")).toBe(29);
    expect(toCents("123456.78")).toBe(12345678);
    expect(dollars(29)).toBe("0.29");
    expect(() => toCents("0.001")).toThrow();
    expect(() => toCents("-1")).toThrow();
    expect(() => toCents("1e3")).toThrow();
    expect(() => toCents("999999999999999999")).toThrow();
  });
  it("sends session CSRF and workspace headers without storing credentials", async () => {
    const fetcher = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ data: { saved: true } }),
    });
    vi.stubGlobal("fetch", fetcher);
    configureSession(
      {
        user: { id: 1, username: "test" },
        workspaces: [],
        demo_mode: true,
        csrfToken: "csrf-test",
      },
      "workspace-test",
    );
    expect(await api("programs/", { method: "POST", body: "{}" })).toEqual({
      saved: true,
    });
    const init = fetcher.mock.calls[0][1];
    expect(init.headers.get("X-CSRFToken")).toBe("csrf-test");
    expect(init.headers.get("X-Workspace-ID")).toBe("workspace-test");
    expect(init.credentials).toBe("same-origin");
    vi.unstubAllGlobals();
  });
  it("surfaces structured backend field errors", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: {
            message: "Invalid input",
            fields: { denominator: "Must be positive" },
          },
        }),
      }),
    );
    await expect(api("imports/")).rejects.toThrow(
      "Denominator: Must be positive",
    );
    vi.unstubAllGlobals();
  });
});
