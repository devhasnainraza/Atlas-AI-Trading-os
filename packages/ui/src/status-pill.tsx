import type { ReactElement } from "react";

export interface StatusPillProps {
  status: "up" | "down" | "degraded" | "unknown";
  label: string;
}

const COLORS: Record<StatusPillProps["status"], string> = {
  up: "#0a7d33",
  degraded: "#9a6700",
  down: "#b42318",
  unknown: "#6b7280",
};

/** Minimal status indicator used by the web shell's health widget. */
export function StatusPill({ status, label }: StatusPillProps): ReactElement {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.4rem",
        padding: "0.15rem 0.6rem",
        borderRadius: "999px",
        border: `1px solid ${COLORS[status]}`,
        color: COLORS[status],
        fontSize: "0.85rem",
      }}
    >
      <span
        style={{
          width: "0.5rem",
          height: "0.5rem",
          borderRadius: "50%",
          background: COLORS[status],
        }}
      />
      {label}
    </span>
  );
}
