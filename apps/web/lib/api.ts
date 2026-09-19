import type { components } from "../../../packages/api-client/schema";
export type Row = { [key: string]: any }; // Dynamic, versioned analysis payloads retain their server-defined fields.
export type Workspace = components["schemas"]["SessionWorkspace"];
export type Session = components["schemas"]["SessionData"];
export type OrganizationRecord = components["schemas"]["Organization"];
export type ProgramRecord = components["schemas"]["Program"];
export type PortfolioRecord = components["schemas"]["Portfolio"];
let csrf = "";
let workspace = "";
export function configureSession(session: Session, id?: string) {
  csrf = session.csrfToken;
  workspace = id ?? session.workspaces[0]?.id ?? "";
}
export function selectWorkspace(id: string) {
  workspace = id;
}
export async function api<T = Row>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers);
  if (workspace) headers.set("X-Workspace-ID", workspace);
  if (options.body && !(options.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (options.method && options.method !== "GET")
    headers.set("X-CSRFToken", csrf);
  const response = await fetch(`/api/v1/${path}`, {
    ...options,
    headers,
    credentials: "same-origin",
    cache: "no-store",
  });
  const content = await response.json().catch(() => null);
  if (!response.ok) {
    const e = content?.error;
    const fields = e?.fields
      ? Object.entries(e.fields)
          .map(
            ([k, v]) =>
              `${label(k)}: ${typeof v === "string" ? v : JSON.stringify(v)}`,
          )
          .join(" · ")
      : "";
    throw new Error(
      [
        e?.message || content?.detail || `Request failed (${response.status})`,
        fields,
      ]
        .filter(Boolean)
        .join(" — "),
    );
  }
  return content.data as T;
}
export const mutate = <T = Row>(
  path: string,
  method: string,
  body: unknown = {},
) => api<T>(path, { method, body: JSON.stringify(body) });
export async function download(path: string, name: string) {
  const response = await fetch(`/api/v1/${path}`, {
    headers: { "X-Workspace-ID": workspace },
    credentials: "same-origin",
  });
  if (!response.ok)
    throw new Error(
      "Export unavailable. The source may have changed or access was withdrawn.",
    );
  const url = URL.createObjectURL(await response.blob());
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}
export const label = (s: string) =>
  s.replaceAll("_", " ").replace(/^./, (c) => c.toUpperCase());
export const money = (value: unknown, cents = false) =>
  value == null
    ? "Unknown"
    : new Intl.NumberFormat("en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: cents ? 2 : 0,
      }).format(Number(value) / (cents ? 100 : 1));
export const date = (value: unknown) =>
  value ? String(value).slice(0, 10) : "Not reported";
export function toCents(value: string): number {
  if (!/^\d+(\.\d{1,2})?$/.test(value))
    throw new Error(
      "Enter a nonnegative USD amount with at most two decimal places.",
    );
  const [whole, fraction = ""] = value.split(".");
  const result = Number(BigInt(whole) * 100n + BigInt(fraction.padEnd(2, "0")));
  if (!Number.isSafeInteger(result)) throw new Error("Amount is too large.");
  return result;
}
export const dollars = (cents: number) =>
  `${Math.floor(cents / 100)}.${String(cents % 100).padStart(2, "0")}`;
