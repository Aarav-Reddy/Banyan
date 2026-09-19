import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Philanthra — Nonprofit research and shared evidence",
  description:
    "Research nonprofit finances, plan funding, and learn from permissioned program evidence.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
