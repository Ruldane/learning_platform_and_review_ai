import { describe, expect, it } from "vitest";
import { dayLoad, formatMinutes, longDay, shortDay } from "./format";

describe("format", () => {
  it.each([
    [690, "11 h 30"],
    [714, "11 h 54"],
    [120, "2 h"],
    [45, "45 min"],
    [0, "0 min"],
    [65, "1 h 05"],
  ])("formats %i minutes as %s", (minutes, expected) => {
    expect(formatMinutes(minutes)).toBe(expected);
  });

  it("names a day in French, whatever the local time zone", () => {
    expect(longDay("2026-11-18")).toBe("mercredi 18 novembre");
    expect(shortDay("2026-11-16")).toBe("lun. 16 nov.");
  });

  it("sums the minutes of a day", () => {
    expect(dayLoad([{ minutes: 30 }, { minutes: 45 }])).toBe(75);
  });
});
