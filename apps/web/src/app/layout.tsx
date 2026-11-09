import type { Metadata } from "next";
import type { ReactNode } from "react";
import "./globals.css";

export const metadata: Metadata = {
  title: "Atlas AI — Autonomous Financial Operations OS",
  description: "Enterprise-grade multi-agent autonomous trading operating system for Forex & Crypto",
  icons: {
    icon: "/favicon.svg",
    apple: "/atlas-logo.jpg",
  },
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" data-theme="light">
      <body>{children}</body>
    </html>
  );
}
