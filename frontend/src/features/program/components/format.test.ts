import { describe, expect, it } from "vitest";
import { dayLoad, dayOfMonth, weekdayLabel } from "./format";

describe("format", () => {
  it("labels a column with the weekday and the day of the month", () => {
    expect(weekdayLabel("2026-11-16")).toBe("lun.");
    expect(dayOfMonth("2026-11-16")).toBe("16");
  });

  it("sums the minutes of a day", () => {
    expect(dayLoad([{ minutes: 30 }, { minutes: 45 }])).toBe(75);
  });
});
