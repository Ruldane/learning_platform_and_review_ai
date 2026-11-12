import { describe, expect, it } from "vitest";
import { makeWeek } from "../fixtures";
import { makeAnnouncements } from "./announcements";

const announcements = makeAnnouncements(makeWeek());
const active = { id: "t1" } as never;
const over = { id: "2026-11-18" } as never;

describe("makeAnnouncements", () => {
  it("names the task and the day in French", () => {
    expect(announcements.onDragStart({ active })).toContain("« Lire le chapitre 1 »");
    expect(announcements.onDragOver({ active, over })).toBe(
      "Tâche « Lire le chapitre 1 » au-dessus de mercredi 18 novembre.",
    );
    expect(announcements.onDragEnd({ active, over })).toBe(
      "Tâche « Lire le chapitre 1 » déposée sur mercredi 18 novembre.",
    );
  });

  it("tells where the task stays when nothing is targeted or the move is cancelled", () => {
    expect(announcements.onDragEnd({ active, over: null })).toBe(
      "Tâche « Lire le chapitre 1 » remise à sa place.",
    );
    expect(announcements.onDragCancel({ active, over: null })).toBe(
      "Déplacement annulé. La tâche « Lire le chapitre 1 » reste sur lundi 16 novembre.",
    );
  });
});
