import type { Metadata } from "next";
import type { ReactNode } from "react";

export const metadata: Metadata = {
  title: "Atlas AI Trading OS",
  description: "AI-first trading operating system — platform foundation shell",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body
        style={{
          margin: 0,
          fontFamily: "system-ui, -apple-system, sans-serif",
          background: "#0b0e14",
          color: "#e6e6e6",
          minHeight: "100vh",
        }}
      >
        <main style={{ maxWidth: 720, margin: "0 auto", padding: "4rem 1.5rem" }}>
          {children}
        </main>
      </body>
    </html>
  );
}
