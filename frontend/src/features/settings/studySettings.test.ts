import { describe, expect, it } from "vitest";
import { settingsFixture } from "./fixtures";
import {
  hasStudyErrors,
  studyDraftErrors,
  timezoneChoices,
  toStudyDraft,
  withStudySettings,
} from "./studySettings";

describe("studySettings", () => {
  it("reads the saved rhythm, review and timezone", () => {
    expect(toStudyDraft(settingsFixture)).toEqual({
      work: "50",
      pause: "10",
      day: "sunday",
      time: "18:00",
      zone: "Europe/Paris",
    });
  });

  it("falls back to the defaults of the back when the review is absent", () => {
    expect(toStudyDraft({ ...settingsFixture, weekly_review: undefined })).toMatchObject({
      day: "sunday",
      time: "18:00",
    });
  });

  it("flags every field outside the contract", () => {
    const base = toStudyDraft(settingsFixture);
    expect(hasStudyErrors(studyDraftErrors(base))).toBe(false);
    expect(studyDraftErrors({ ...base, work: "9" }).work).toBe(true);
    expect(studyDraftErrors({ ...base, work: "121" }).work).toBe(true);
    expect(studyDraftErrors({ ...base, work: "" }).work).toBe(true);
    expect(studyDraftErrors({ ...base, work: "12.5" }).work).toBe(true);
    expect(studyDraftErrors({ ...base, pause: "61" }).pause).toBe(true);
    expect(studyDraftErrors({ ...base, pause: "0" }).pause).toBe(false);
    expect(studyDraftErrors({ ...base, time: "24:00" }).time).toBe(true);
    expect(studyDraftErrors({ ...base, time: "7:00" }).time).toBe(true);
    expect(studyDraftErrors({ ...base, zone: "" }).zone).toBe(true);
  });

  it("builds a full body that keeps the other settings", () => {
    const body = withStudySettings(settingsFixture, {
      work: "45",
      pause: "5",
      day: "friday",
      time: "17:15",
      zone: "Asia/Tokyo",
    });
    expect(body).toMatchObject({
      study_work_minutes: 45,
      study_break_minutes: 5,
      weekly_review: { day: "friday", time: "17:15" },
      timezone: "Asia/Tokyo",
      debate_rounds: 3,
      brief_time: "07:00",
      tiers: settingsFixture.tiers,
    });
  });

  it("keeps the current timezone in the list even when the browser does not know it", () => {
    expect(timezoneChoices("Europe/Paris")).toContain("Europe/Paris");
    expect(timezoneChoices("Etc/Zoulou")[0]).toBe("Etc/Zoulou");
  });
});
