import { describe, expect, it } from "vitest";
import {
  availabilityErrors,
  delaysInvalid,
  hasAvailabilityErrors,
  toAvailabilityDraft,
  weeklyBudget,
  withAvailabilitySettings,
} from "./availabilitySettings";
import { settingsFixture } from "./fixtures";

const draft = () => toAvailabilityDraft(settingsFixture);
const bad = (over: object) => hasAvailabilityErrors(availabilityErrors({ ...draft(), ...over }));

describe("availability draft", () => {
  it("reads the settings and writes them back as a full body", () => {
    expect(draft()).toEqual({
      weekday: "120",
      weekendMin: "180",
      weekendMax: "240",
      briefTime: "07:00",
      delays: ["7", "14", "21"],
      rounds: "3",
      tokenCap: "300000",
      lessonLanguage: "fr",
    });
    const body = withAvailabilitySettings(settingsFixture, { ...draft(), weekday: "90" });
    expect(body.availability).toEqual({
      weekday_minutes: 90,
      weekend_block_min_minutes: 180,
      weekend_block_max_minutes: 240,
    });
    expect(body.reminder_delays_days).toEqual([7, 14, 21]);
    expect(body.tiers).toEqual(settingsFixture.tiers);
    expect(body).not.toHaveProperty("vision_enabled");
  });

  it("computes the weekly budget: five weekdays plus the longest weekend block", () => {
    expect(weeklyBudget(draft())).toBe(840);
    expect(weeklyBudget({ ...draft(), weekday: "60", weekendMax: "300" })).toBe(600);
    expect(weeklyBudget({ ...draft(), weekday: "" })).toBeNull();
    expect(weeklyBudget({ ...draft(), weekendMax: "1441" })).toBeNull();
  });

  it("accepts the stored values and refuses what the contract refuses", () => {
    expect(bad({})).toBe(false);
    expect(bad({ weekday: "1441" })).toBe(true);
    expect(bad({ weekday: "-1" })).toBe(true);
    expect(bad({ weekday: "1.5" })).toBe(true);
    expect(bad({ weekendMin: "300" })).toBe(true); // minimum au-dessus du maximum
    expect(bad({ briefTime: "25:00" })).toBe(true);
    expect(bad({ rounds: "0" })).toBe(true);
    expect(bad({ rounds: "6" })).toBe(true);
    expect(bad({ tokenCap: "9999" })).toBe(true);
    expect(bad({ tokenCap: "10000" })).toBe(false);
    expect(bad({ lessonLanguage: "" })).toBe(true);
  });

  it("flags the order of the weekend block on both fields", () => {
    const errors = availabilityErrors({ ...draft(), weekendMin: "300" });
    expect([errors.weekendOrder, errors.weekendMin, errors.weekendMax]).toEqual([true, true, true]);
  });

  it("wants three strictly increasing delays between 1 and 90 days", () => {
    expect(delaysInvalid(["7", "14", "21"])).toBe(false);
    expect(delaysInvalid(["1", "2", "90"])).toBe(false);
    expect(delaysInvalid(["7", "7", "21"])).toBe(true);
    expect(delaysInvalid(["21", "14", "7"])).toBe(true);
    expect(delaysInvalid(["0", "14", "21"])).toBe(true);
    expect(delaysInvalid(["7", "14", "91"])).toBe(true);
    expect(delaysInvalid(["7", "", "21"])).toBe(true);
  });
});
