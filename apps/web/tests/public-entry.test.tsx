import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { Application } from "../components/application";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn() }),
  useSearchParams: () => new URLSearchParams(),
}));
afterEach(() => vi.unstubAllGlobals());
function session(demo: boolean, readOnly = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        data: {
          user: null,
          workspaces: [],
          demo_mode: demo,
          demo_read_only: readOnly,
          csrfToken: "synthetic-csrf",
        },
      }),
    }),
  );
}
describe("Public and demo entry preserve their original gates", () => {
  it("shows all four demo role entry actions only in demo mode", async () => {
    session(true);
    render(<Application path={["demo"]} />);
    for (const role of [
      "Foundation administrator",
      "Nonprofit owner",
      "Assigned reviewer",
      "Read-only foundation viewer",
    ])
      expect(
        await screen.findByRole("button", { name: new RegExp(role) }),
      ).toBeVisible();
    expect(screen.getByRole("button", { name: "Sign in" })).toBeVisible();
    expect(screen.getByText(/Isolated demo/)).toBeVisible();
  });
  it("retains ordinary sign-in without exposing demo roles when demo mode is off", async () => {
    session(false);
    render(<Application path={["demo"]} />);
    expect(await screen.findByLabelText("Username")).toBeRequired();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "autocomplete",
      "current-password",
    );
    expect(
      screen.queryByText("Explore with a demo role"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Demo sign-in credentials" }),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByText("Demo-only-Philanthra-2026!"),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "Forgot your password?" }),
    ).toHaveAttribute("href", "/password-reset");
  });
  it("keeps invitation fields and submission separate from demo sign-in", async () => {
    session(true);
    render(<Application path={["join"]} />);
    expect(await screen.findByLabelText("Invitation token")).toBeRequired();
    expect(screen.getByLabelText("Password")).toHaveAttribute(
      "autocomplete",
      "new-password",
    );
    expect(
      screen.getByRole("button", { name: "Join workspace" }),
    ).toBeVisible();
    expect(
      screen.queryByText("Explore with a demo role"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Demo sign-in credentials" }),
    ).not.toBeInTheDocument();
  });
  it.each(["login", "demo"])(
    "shows all three credentials and the read-only boundary on /%s",
    async (path) => {
      session(true, true);
      render(<Application path={[path]} />);
      const table = await screen.findByRole("table", {
        name: "Demo sign-in credentials",
      });
      const rows = within(table).getAllByRole("row").slice(1);
      expect(rows).toHaveLength(3);
      for (const [index, username] of [
        "foundation-admin",
        "ngo-owner",
        "reviewer",
      ].entries()) {
        expect(within(rows[index]).getByText(username)).toBeVisible();
        expect(
          within(rows[index]).getByText("Demo-only-Philanthra-2026!"),
        ).toBeVisible();
      }
      expect(screen.getByText(/This public demo is read-only/)).toBeVisible();
    },
  );
});
