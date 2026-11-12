import type { ApiKeyOut, ModelChoice, ModelsOut, SettingsOut } from "./types";

/** Données de test de la feature (réponses typiques du back) ; jamais importées par le code de l'application. */
function allTiers(provider: string, model: string) {
  const choice: ModelChoice = { provider, model };
  return { rapide: choice, standard: choice, fort: choice, vision: choice };
}

export const settingsFixture: SettingsOut = {
  agent_overrides: {},
  availability: {
    weekday_minutes: 120,
    weekend_block_min_minutes: 180,
    weekend_block_max_minutes: 240,
    weekly_budget_minutes: 840,
  },
  brief_time: "07:00",
  debate_rounds: 3,
  excluded_domains: [],
  lesson_language: "fr",
  preferred_domains: [],
  reminder_delays_days: [7, 14, 21],
  search_languages: ["fr", "en"],
  search_max_pages: 30,
  search_max_queries: 12,
  search_provider_order: ["searxng", "brave"],
  session_token_cap: 300_000,
  style_guide: "",
  tiers: allTiers("anthropic", "claude-haiku-5-5"),
  vision_enabled: true,
  weekly_review: { day: "sunday", time: "18:00" },
};

export const apiKeysFixture: ApiKeyOut[] = [
  {
    provider: "anthropic",
    label: "Anthropic",
    source: "ui",
    last4: "9876",
    readable: true,
    last_test_ok: null,
    last_tested_at: null,
  },
  {
    provider: "openai",
    label: "OpenAI",
    source: "env",
    last4: "abcd",
    readable: true,
    last_test_ok: true,
    last_tested_at: null,
  },
  {
    provider: "glm",
    label: "GLM (Z.ai)",
    source: null,
    last4: null,
    readable: true,
    last_test_ok: null,
    last_tested_at: null,
  },
];

export const modelsFixture: ModelsOut = {
  providers: [
    {
      name: "anthropic",
      label: "Anthropic",
      has_key: true,
      models: ["claude-haiku-5-5", "claude-sonnet-5-5"],
    },
    { name: "openai", label: "OpenAI", has_key: true, models: ["gpt-6-luna", "gpt-6.1-sol"] },
    { name: "glm", label: "GLM (Z.ai)", has_key: false, models: null },
  ],
  presets: {
    all_haiku: allTiers("anthropic", "claude-haiku-5-5"),
    haiku_sonnet_strong: {
      ...allTiers("anthropic", "claude-haiku-5-5"),
      fort: { provider: "anthropic", model: "claude-sonnet-5-5" },
    },
    all_glm: allTiers("glm", "glm-5.3"),
    all_openai: allTiers("openai", "gpt-6-luna"),
  },
};
