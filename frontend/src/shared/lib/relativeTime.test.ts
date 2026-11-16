import { describe, expect, it } from "vitest";
import { clockTime, fullDateTime, longDate, relativeTime } from "./relativeTime";

const NOW = new Date("2026-11-16T12:00:00Z");

describe("relativeTime", () => {
  it.each([
    ["2026-11-16T11:55:00Z", "il y a 5 min"],
    ["2026-11-16T09:00:00Z", "il y a 3 h"],
    ["2026-11-14T12:00:00Z", "il y a 2 j"],
    ["2026-11-16T11:59:30Z", "à l'instant"],
    ["2026-11-16T12:30:00Z", "à l'instant"],
  ])("writes %s as %s", (iso, expected) => {
    expect(relativeTime(iso, NOW)).toBe(expected);
  });

  it("returns an unreadable instant as is", () => {
    expect(relativeTime("n'importe quoi", NOW)).toBe("n'importe quoi");
    expect(fullDateTime("n'importe quoi")).toBe("n'importe quoi");
    expect(longDate("n'importe quoi")).toBe("n'importe quoi");
    expect(clockTime("n'importe quoi")).toBe("n'importe quoi");
  });

  it("writes a full date, a day and a clock time in French", () => {
    expect(fullDateTime("2026-11-16T10:05:00Z")).toMatch(/16 novembre 2026/);
    expect(longDate("2026-11-10")).toBe("10 novembre 2026");
    expect(clockTime("2026-11-16T07:00:00Z")).toMatch(/^\d{2}:\d{2}$/);
  });
});
