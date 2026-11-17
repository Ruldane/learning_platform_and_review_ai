import { describe, expect, it } from "vitest";
import { settingsFixture } from "./fixtures";
import { toAvailabilityDraft, withAvailabilitySettings } from "./availabilitySettings";
import { toStudyDraft, withStudySettings } from "./studySettings";
import {
  buildUserSettings,
  toBraveUsageView,
  toSearchSettingsView,
  withAgentOverride,
  withSearchSettings,
  withStyleGuide,
} from "./userSettings";

const newTiers = {
  rapide: { provider: "glm", model: "glm-4.7-flash" },
  standard: { provider: "glm", model: "glm-4.7-flash" },
  fort: { provider: "glm", model: "glm-5.3" },
  vision: { provider: "glm", model: "glm-5.3-flash" },
};

describe("buildUserSettings", () => {
  it("remplace les niveaux et reprend tous les autres réglages", () => {
    const body = buildUserSettings(settingsFixture, newTiers);
    expect(body.tiers).toEqual(newTiers);
    expect(body.brief_time).toBe("07:00");
    expect(body.debate_rounds).toBe(3);
    expect(body.reminder_delays_days).toEqual([7, 14, 21]);
    expect(body.search_provider_order).toEqual(["searxng", "brave"]);
    expect(body.weekly_review).toEqual({ day: "sunday", time: "18:00" });
  });

  it("ne contient aucun champ calculé en lecture seule", () => {
    const body = buildUserSettings(settingsFixture, newTiers);
    expect(body).not.toHaveProperty("vision_enabled");
    expect(body.availability).toEqual({
      weekday_minutes: 120,
      weekend_block_min_minutes: 180,
      weekend_block_max_minutes: 240,
    });
    expect(body.availability).not.toHaveProperty("weekly_budget_minutes");
  });

  it("n'a que les champs de UserSettings", () => {
    expect(Object.keys(buildUserSettings(settingsFixture, newTiers)).sort()).toEqual([
      "agent_overrides",
      "availability",
      "brief_time",
      "debate_rounds",
      "excluded_domains",
      "lesson_language",
      "onboarding_done",
      "preferred_domains",
      "radar_role",
      "radar_zone",
      "reminder_delays_days",
      "search_languages",
      "search_max_pages",
      "search_max_queries",
      "search_provider_order",
      "session_token_cap",
      "study_break_minutes",
      "study_work_minutes",
      "style_guide",
      "tiers",
      "timezone",
      "weekly_review",
    ]);
  });

  it("garde le poste et la zone du radar tels quels (un PUT complet ne les efface pas)", () => {
    const current = { ...settingsFixture, radar_role: "Ingénieur IA", radar_zone: "Lyon" };
    const body = buildUserSettings(current, newTiers);
    expect([body.radar_role, body.radar_zone]).toEqual(["Ingénieur IA", "Lyon"]);
  });

  it("garde le rythme d'étude et le fuseau tels quels", () => {
    const current = { ...settingsFixture, study_work_minutes: 25, timezone: "America/New_York" };
    const body = buildUserSettings(current, newTiers);
    expect([body.study_work_minutes, body.study_break_minutes, body.timezone]).toEqual([
      25,
      10,
      "America/New_York",
    ]);
  });
});

describe("réglages de recherche", () => {
  const view = {
    languages: ["fr", "en", "es"],
    preferred: ["python.org"],
    excluded: ["example.com"],
    order: ["searxng", "brave"] as ("searxng" | "brave")[],
    maxQueries: 20,
    maxPages: 40,
  };

  it("lit les réglages de recherche, avec les valeurs par défaut du back si absentes", () => {
    expect(toSearchSettingsView(settingsFixture)).toEqual({
      languages: ["fr", "en"],
      preferred: [],
      excluded: [],
      order: ["searxng", "brave"],
      maxQueries: 12,
      maxPages: 30,
    });
    const bare = {
      ...settingsFixture,
      search_languages: undefined,
      search_provider_order: undefined,
    };
    expect(toSearchSettingsView(bare).languages).toEqual(["fr", "en"]);
  });

  it("remplace les seuls champs de recherche et reprend tout le reste", () => {
    const body = withSearchSettings(settingsFixture, view);
    expect(body).toMatchObject({
      search_languages: ["fr", "en", "es"],
      preferred_domains: ["python.org"],
      excluded_domains: ["example.com"],
      search_provider_order: ["searxng", "brave"],
      search_max_queries: 20,
      search_max_pages: 40,
      tiers: settingsFixture.tiers,
      brief_time: "07:00",
      weekly_review: { day: "sunday", time: "18:00" },
    });
    expect(body).not.toHaveProperty("vision_enabled");
    expect(Object.keys(body).sort()).toEqual(
      Object.keys(buildUserSettings(settingsFixture, settingsFixture.tiers as never)).sort(),
    );
  });

  it("convertit le compteur Brave du contrat", () => {
    expect(
      toBraveUsageView({ brave: { has_key: true, used: 3, cap: 900, month: "2026-11" } }),
    ).toEqual({ hasKey: true, used: 3, cap: 900, month: "2026-11" });
  });
});

describe("onboarding_done and agent_overrides survive every full PUT (focus 5)", () => {
  const override = { provider: "openai", model: "gpt-6-luna" };
  const current = {
    ...settingsFixture,
    onboarding_done: true,
    agent_overrides: { tutor: override },
  };

  it("buildUserSettings keeps onboarding_done and agent_overrides", () => {
    const body = buildUserSettings(current, newTiers);
    expect(body.onboarding_done).toBe(true);
    expect(body.agent_overrides).toEqual({ tutor: override });
    // Jamais forcé : le front ne décide pas à la place du back que le premier lancement est fait.
    const fresh = buildUserSettings({ ...settingsFixture, onboarding_done: false }, newTiers);
    expect(fresh.onboarding_done).toBe(false);
  });

  it("every other builder of the settings pages keeps them too", () => {
    const bodies = [
      withSearchSettings(current, toSearchSettingsView(current)),
      withStudySettings(current, toStudyDraft(current)),
      withAvailabilitySettings(current, toAvailabilityDraft(current)),
      withStyleGuide(current, "Phrases courtes."),
    ];
    for (const body of bodies) {
      expect(body.onboarding_done).toBe(true);
      expect(body.agent_overrides).toEqual({ tutor: override });
    }
  });
});

describe("withAgentOverride", () => {
  const tutor = { provider: "openai", model: "gpt-6-luna" };
  const other = { provider: "glm", model: "glm-5.3" };
  const current = { ...settingsFixture, agent_overrides: { tutor } };

  it("adds or replaces the override of one agent and keeps the others", () => {
    expect(withAgentOverride(current, "scout", other).agent_overrides).toEqual({
      tutor,
      scout: other,
    });
    expect(withAgentOverride(current, "tutor", other).agent_overrides).toEqual({ tutor: other });
  });

  it("removes the override of an agent with null, and only that one", () => {
    expect(withAgentOverride(current, "tutor", null).agent_overrides).toEqual({});
    expect(withAgentOverride(current, "scout", null).agent_overrides).toEqual({ tutor });
  });

  it("keeps the tiers and the other settings", () => {
    const body = withAgentOverride(current, "scout", other);
    expect(body.tiers).toEqual(current.tiers);
    expect(body.brief_time).toBe("07:00");
    expect(body).not.toHaveProperty("vision_enabled");
  });
});
