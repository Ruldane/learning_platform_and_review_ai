import { describe, expect, it } from "vitest";
import { todayString } from "./dates";

describe("todayString", () => {
  it("is the local day as AAAA-MM-JJ, with zeros", () => {
    expect(todayString(new Date(2026, 0, 5, 23, 59))).toBe("2026-01-05");
    expect(todayString(new Date(2026, 10, 15, 0, 1))).toBe("2026-11-15");
  });
});
