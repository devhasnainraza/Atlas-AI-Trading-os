import { StatusPill } from "@atlas/ui";

interface Readiness {
  status: "ready" | "degraded" | "down";
  dependencies: Array<{ name: string; status: "up" | "down"; latency_ms: number }>;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchReadiness(): Promise<Readiness | null> {
  try {
    const resp = await fetch(`${API_URL}/v1/health/ready`, { cache: "no-store" });
    return (await resp.json()) as Readiness;
  } catch {
    return null;
  }
}

export default async function HomePage() {
  const readiness = await fetchReadiness();

  return (
    <>
      <h1 style={{ fontSize: "1.6rem", marginBottom: "0.25rem" }}>Atlas AI Trading OS</h1>
      <p style={{ color: "#9aa4b2", marginTop: 0 }}>
        Platform foundation shell — Spec 00. Feature UIs arrive with their specs.
      </p>

      <section
        style={{
          marginTop: "2.5rem",
          padding: "1.25rem",
          border: "1px solid #1f2733",
          borderRadius: "12px",
          background: "#101521",
        }}
      >
        <h2 style={{ fontSize: "1rem", marginTop: 0 }}>Platform health</h2>
        {readiness === null ? (
          <StatusPill status="unknown" label="API unreachable" />
        ) : (
          <>
            <StatusPill
              status={readiness.status === "ready" ? "up" : "degraded"}
              label={`API: ${readiness.status}`}
            />
            <ul style={{ listStyle: "none", padding: 0, marginBottom: 0 }}>
              {readiness.dependencies.map((dep) => (
                <li key={dep.name} style={{ marginTop: "0.5rem" }}>
                  <StatusPill
                    status={dep.status}
                    label={`${dep.name} · ${dep.latency_ms}ms`}
                  />
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </>
  );
}
