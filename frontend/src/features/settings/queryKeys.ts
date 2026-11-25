/** TanStack Query keys of the feature (never sensitive data in them). */
export const settingsKeys = {
  settings: ["settings"],
  apiKeys: ["api-keys"],
  models: ["models"],
  agents: ["agents"],
  searchUsage: ["search-usage"],
  /** Read on the home page only (first-run step 1), at their own pace. */
  onboardingHealth: ["onboarding", "health"],
  onboardingEmbedding: ["onboarding", "embedding"],
} as const;
