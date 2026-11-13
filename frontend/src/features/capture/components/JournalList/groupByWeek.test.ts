import { describe, expect, it } from "vitest";
import type { JournalEntryView } from "../viewTypes";
import { groupByWeek, weekStartOf } from "./groupByWeek";

const entry = (id: string, occurredOn: string, kind: JournalEntryView["kind"] = "capture") => ({
  id,
  kind,
  text: id,
  occurredOn,
  studySessionId: null,
  memoryItemId: null,
});

describe("groupByWeek", () => {
  it("finds the Monday of any day, Sunday included", () => {
    expect(weekStartOf("2026-11-16")).toBe("2026-11-16");
    expect(weekStartOf("2026-11-22")).toBe("2026-11-16");
    expect(weekStartOf("2026-11-23")).toBe("2026-11-23");
  });

  it("groups by week, most recent first, with the weekly review at the top", () => {
    const weeks = groupByWeek([
      entry("a", "2026-11-24"),
      entry("b", "2026-11-23", "weekly_review"),
      entry("c", "2026-11-22"),
      entry("d", "2026-11-17", "study_session"),
    ]);
    expect(weeks.map((week) => week.weekStart)).toEqual(["2026-11-23", "2026-11-16"]);
    expect(weeks[0]?.entries.map((item) => item.id)).toEqual(["b", "a"]);
    expect(weeks[1]?.entries.map((item) => item.id)).toEqual(["c", "d"]);
  });

  it("merges a week split over two pages", () => {
    const weeks = groupByWeek([entry("a", "2026-11-18"), entry("b", "2026-11-17")]);
    expect(weeks).toHaveLength(1);
    expect(weeks[0]?.entries).toHaveLength(2);
  });
});
