import { describe, expect, it } from "vitest";
import { settingsFixture } from "./fixtures";
import { withOnboardingDone } from "./onboarding";
import { buildUserSettings } from "./userSettings";
import { readTiers } from "./tierChoices";

const fresh = { ...settingsFixture, onboarding_done: false };
const override = { provider: "openai", model: "gpt-6-luna" };

describe("withOnboardingDone", () => {
  it("marks the onboarding done and keeps every other setting", () => {
    const current = { ...fresh, agent_overrides: { tutor: override }, style_guide: "Tutoiement." };
    const body = withOnboardingDone(current);
    expect(body).toEqual({
      ...buildUserSettings(current, readTiers(current.tiers)),
      onboarding_done: true,
    });
    expect(body.agent_overrides).toEqual({ tutor: override });
    expect(body.style_guide).toBe("Tutoiement.");
  });

  it("leaves the availability as read when none is given", () => {
    expect(withOnboardingDone(fresh).availability).toEqual({
      weekday_minutes: 120,
      weekend_block_min_minutes: 180,
      weekend_block_max_minutes: 240,
    });
  });

  it("writes the three durations given, as numbers, and nothing calculated", () => {
    const body = withOnboardingDone(fresh, { weekday: "90", weekendMin: "60", weekendMax: "300" });
    expect(body.availability).toEqual({
      weekday_minutes: 90,
      weekend_block_min_minutes: 60,
      weekend_block_max_minutes: 300,
    });
    expect(body).not.toHaveProperty("vision_enabled");
    expect(body.brief_time).toBe("07:00");
  });
});
