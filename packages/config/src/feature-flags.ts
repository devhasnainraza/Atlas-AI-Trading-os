/**
 * Frontend feature-flag client (Spec 00 US6, FR-040).
 *
 * Mirrors the backend contract: evaluation always carries a caller-declared safe default;
 * network or server failure can never break the UI — it falls back (ERROR_FALLBACK).
 */

export type FlagReason =
  | "TARGETING_MATCH"
  | "DEFAULT"
  | "DISABLED"
  | "ERROR_FALLBACK";

export interface FlagEvaluation<T> {
  flagKey: string;
  value: T;
  reason: FlagReason;
}

export interface FlagClientOptions {
  /** Base URL of the Atlas API, e.g. http://localhost:8000 */
  apiBaseUrl: string;
  /** Per-request timeout in milliseconds (default 2000). */
  timeoutMs?: number;
}

export class FeatureFlagClient {
  private readonly baseUrl: string;
  private readonly timeoutMs: number;

  constructor(options: FlagClientOptions) {
    this.baseUrl = options.apiBaseUrl.replace(/\/$/, "");
    this.timeoutMs = options.timeoutMs ?? 2000;
  }

  async evaluate<T>(flagKey: string, defaultValue: T): Promise<FlagEvaluation<T>> {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeoutMs);
      const response = await fetch(
        `${this.baseUrl}/v1/feature-flags/${encodeURIComponent(flagKey)}/evaluation`,
        { signal: controller.signal },
      );
      clearTimeout(timer);
      if (!response.ok) {
        return { flagKey, value: defaultValue, reason: "ERROR_FALLBACK" };
      }
      const body = (await response.json()) as { value: T; reason: FlagReason };
      return { flagKey, value: body.value, reason: body.reason };
    } catch {
      return { flagKey, value: defaultValue, reason: "ERROR_FALLBACK" };
    }
  }

  async isEnabled(flagKey: string, defaultValue = false): Promise<boolean> {
    const evaluation = await this.evaluate(flagKey, defaultValue);
    return Boolean(evaluation.value);
  }
}
