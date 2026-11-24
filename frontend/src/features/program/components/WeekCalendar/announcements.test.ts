import { describe, expect, it } from "vitest";
import { makeWeek } from "../fixtures";
import { makeAnnouncements } from "./announcements";

const announcements = makeAnnouncements(makeWeek());
const active = { id: "t1" } as never;
const over = { id: "2026-11-18" } as never;

describe("makeAnnouncements", () => {
  it("names the task and the day in English", () => {
    expect(announcements.onDragStart({ active })).toContain("“Lire le chapitre 1”");
    expect(announcements.onDragOver({ active, over })).toBe(
      "Task “Lire le chapitre 1” is over Wednesday 18 November.",
    );
    expect(announcements.onDragEnd({ active, over })).toBe(
      "Task “Lire le chapitre 1” dropped on Wednesday 18 November.",
    );
  });

  it("tells where the task stays when nothing is targeted or the move is cancelled", () => {
    expect(announcements.onDragEnd({ active, over: null })).toBe(
      "Task “Lire le chapitre 1” returned to its place.",
    );
    expect(announcements.onDragCancel({ active, over: null })).toBe(
      "Move cancelled. Task “Lire le chapitre 1” stays on Monday 16 November.",
    );
  });
});
