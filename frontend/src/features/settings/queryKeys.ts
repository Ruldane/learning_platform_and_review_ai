/** Clés TanStack Query de la feature (jamais de donnée sensible dedans). */
export const settingsKeys = {
  settings: ["settings"],
  apiKeys: ["api-keys"],
  models: ["models"],
  agents: ["agents"],
  searchUsage: ["search-usage"],
  /** Lus à l'accueil seulement (étape 1 du premier lancement), à leur propre rythme. */
  onboardingHealth: ["onboarding", "health"],
  onboardingEmbedding: ["onboarding", "embedding"],
} as const;
