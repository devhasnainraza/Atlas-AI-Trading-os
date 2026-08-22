/**
 * Typed Atlas API client (Spec 00 US4, FR-013).
 *
 * `schema.d.ts` is generated from the backend OpenAPI by `scripts/generate-client`
 * (CI regenerates on every contract change so type drift fails the build, not runtime).
 * This hand-written core stays tiny: fetch wrapper + the platform error envelope.
 */

export interface AtlasErrorEnvelope {
  error: {
    code: string;
    message: string;
    correlation_id: string;
    details?: Array<{ field?: string; issue?: string }>;
  };
}

export class AtlasApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly envelope: AtlasErrorEnvelope,
  ) {
    super(envelope.error.message);
    this.name = "AtlasApiError";
  }

  get code(): string {
    return this.envelope.error.code;
  }

  get correlationId(): string {
    return this.envelope.error.correlation_id;
  }
}

export interface AtlasClientOptions {
  baseUrl: string;
  getAuthToken?: () => string | undefined;
}

export class AtlasClient {
  constructor(private readonly options: AtlasClientOptions) {}

  async request<T>(path: string, init: RequestInit = {}): Promise<T> {
    const headers = new Headers(init.headers);
    headers.set("Content-Type", "application/json");
    const token = this.options.getAuthToken?.();
    if (token) headers.set("Authorization", `Bearer ${token}`);

    const response = await fetch(`${this.options.baseUrl.replace(/\/$/, "")}${path}`, {
      ...init,
      headers,
    });

    if (!response.ok) {
      const envelope = (await response.json().catch(() => null)) as AtlasErrorEnvelope | null;
      throw new AtlasApiError(
        response.status,
        envelope ?? {
          error: {
            code: "ATLAS-CLIENT-001",
            message: `Request failed with status ${response.status}`,
            correlation_id: response.headers.get("X-Correlation-ID") ?? "",
          },
        },
      );
    }
    if (response.status === 204) return undefined as T;
    return (await response.json()) as T;
  }

  get<T>(path: string): Promise<T> {
    return this.request<T>(path);
  }

  post<T>(path: string, body?: unknown): Promise<T> {
    return this.request<T>(path, { method: "POST", body: JSON.stringify(body ?? {}) });
  }
}
