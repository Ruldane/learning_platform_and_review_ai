import { describe, expect, it } from "vitest";
import { settingsFixture } from "./fixtures";
import { buildUserSettings } from "./userSettings";

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
      "preferred_domains",
      "reminder_delays_days",
      "search_languages",
      "search_provider_order",
      "session_token_cap",
      "style_guide",
      "tiers",
      "weekly_review",
    ]);
  });
});
