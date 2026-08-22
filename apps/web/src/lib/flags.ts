/**
 * Web flag access (US6): one shared client instance; every call site declares its safe
 * default so a flag-service outage can never break the UI.
 */

import { FeatureFlagClient } from "@atlas/config/feature-flags";

export const flags = new FeatureFlagClient({
  apiBaseUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000",
});
