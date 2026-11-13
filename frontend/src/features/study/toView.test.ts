import { describe, expect, it } from "vitest";
import { clampQuestion, openSessionIn, toBlockView, toSummaryView, toTutorOptions } from "./toView";
import type { StudySessionOut } from "./types";

const session: StudySessionOut = {
  id: "st1",
  lesson_id: "l1",
  lesson_title: "Les API REST",
  module_title: "Web",
  mode: "socratic",
  status: "finished",
  session_id: "s1",
  started_at: "2026-11-17T10:00:00Z",
  ended_at: "2026-11-17T10:50:00Z",
  minutes: 48,
  summary: null,
  tasks_done: ["Lire la leçon"],
  flashcards_created: 3,
  skills: [{ name: "REST", level: "en_cours" }],
};

describe("toView", () => {
  it("maps the block of the day", () => {
    expect(
      toBlockView({
        lesson_id: "l1",
        lesson_title: "Les API REST",
        module_title: "Web",
        tasks: [{ id: "t1", title: "Lire", minutes: 30, type: "lire" }],
      }),
    ).toEqual({
      lessonTitle: "Les API REST",
      moduleTitle: "Web",
      tasks: [{ id: "t1", title: "Lire", minutes: 30, type: "lire" }],
    });
  });

  it("maps the end summary and turns a missing summary into an empty text", () => {
    expect(toSummaryView(session)).toEqual({
      moduleTitle: "Web",
      lessonTitle: "Les API REST",
      minutes: 48,
      summary: "",
      tasksDone: ["Lire la leçon"],
      flashcardsCreated: 3,
      skills: [{ name: "REST", level: "en_cours" }],
    });
  });

  it("keeps the option labels of the back as they are", () => {
    expect(toTutorOptions([{ value: "stuck", label: "Je bloque (2/3)" }])).toEqual([
      { value: "stuck", label: "Je bloque (2/3)" },
    ]);
    expect(toTutorOptions(undefined)).toEqual([]);
  });

  it("cuts a passage at 2000 characters without splitting a character", () => {
    expect(clampQuestion("  court  ")).toBe("court");
    const long = "𝒳".repeat(2500);
    expect(Array.from(clampQuestion(long))).toHaveLength(2000);
  });

  it("reads the open session id of a 409", () => {
    expect(openSessionIn({ study_session_id: "st9" })).toBe("st9");
    expect(openSessionIn(null)).toBeNull();
    expect(openSessionIn({ study_session_id: 3 })).toBeNull();
  });
});
