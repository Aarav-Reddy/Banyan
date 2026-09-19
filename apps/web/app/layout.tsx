import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "Philanthra — Evidence for better giving",
  description:
    "Connect funding decisions with permissioned nonprofit learning.",
};
export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
