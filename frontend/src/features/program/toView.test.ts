import { describe, expect, it } from "vitest";
import { moduleOut, programOut, taskOut, weekOut } from "@/test/programApi";
import type { ProgramOut } from "./types";
import {
  moduleForDate,
  toModuleLessons,
  toPlanDiffView,
  toProgressView,
  toWeekViews,
} from "./toView";

const BUDGET = { weekday: 120, weekend: 240 };
const program = (over: Record<string, unknown> = {}) => programOut(over) as unknown as ProgramOut;

describe("toWeekViews", () => {
  it("builds seven days from Monday, with the weekday, Saturday and Sunday capacities", () => {
    const [week] = toWeekViews(program(), BUDGET);
    expect(week?.days.map((day) => day.date)).toEqual([
      "2026-11-16",
      "2026-11-17",
      "2026-11-18",
      "2026-11-19",
      "2026-11-20",
      "2026-11-21",
      "2026-11-22",
    ]);
    expect(week?.days.map((day) => day.capacityMinutes)).toEqual([120, 120, 120, 120, 120, 240, 0]);
    expect(week).toMatchObject({ rank: 1, capMinutes: 714, startDate: "2026-11-16" });
  });

  it("places the tasks by planned date, not by module", () => {
    const moved = program({
      weeks: [
        weekOut({
          modules: [
            moduleOut({
              tasks: [taskOut({ id: "t1", planned_date: "2026-11-24", title: "Déplacée" })],
            }),
          ],
        }),
        weekOut({ id: "w2", rank: 2, start_date: "2026-11-23", modules: [] }),
      ],
    });
    const [first, second] = toWeekViews(moved, BUDGET);
    expect(first?.days.flatMap((day) => day.tasks)).toHaveLength(0);
    const tuesday = second?.days[1];
    expect(tuesday?.date).toBe("2026-11-24");
    expect(tuesday?.tasks[0]).toMatchObject({
      id: "t1",
      title: "Déplacée",
      moduleTitle: "Bases du langage",
    });
    expect(second?.loadMinutes).toBe(60);
  });

  it("maps a task to its view, load included", () => {
    const [week] = toWeekViews(program(), BUDGET);
    expect(week?.loadMinutes).toBe(180);
    expect(week?.days[0]?.tasks[0]).toEqual({
      id: "t1",
      moduleTitle: "Bases du langage",
      title: "Lire le chapitre 1",
      type: "lire",
      minutes: 60,
      doneCriterion: "Je sais expliquer les variables.",
      plannedDate: "2026-11-16",
      done: false,
      alreadyKnown: false,
    });
  });

  it("marks a done task and an already-known one", () => {
    const weeks = toWeekViews(program(), BUDGET);
    expect(weeks[1]?.days[1]?.tasks[0]?.done).toBe(true);
    const known = program({
      weeks: [weekOut({ modules: [moduleOut({ tasks: [taskOut({ already_known: true })] })] })],
    });
    expect(toWeekViews(known, BUDGET)[0]?.days[0]?.tasks[0]?.alreadyKnown).toBe(true);
  });
});

describe("toProgressView", () => {
  it("renames the server counters", () => {
    expect(toProgressView(program().progress)).toEqual({
      tasksDone: 1,
      tasksPlanned: 5,
      minutesDone: 60,
      minutesPlanned: 300,
    });
  });
});

describe("toPlanDiffView", () => {
  const diff = {
    added: ["Fichiers CSV / Lire le module csv", "Sans module"],
    removed: ["Bases du langage / Regarder la vidéo 3"],
    moved: [
      { task: "Bases du langage / Lire le chapitre 1", before: "2026-11-16", after: "2026-11-18" },
    ],
    weeks_before: 2,
    weeks_after: 2,
  };

  it("splits « module / tâche » and finds the planned day of an added task", () => {
    const view = toPlanDiffView(diff, program());
    expect(view.added[0]).toMatchObject({
      title: "Lire le module csv",
      moduleTitle: "Fichiers CSV",
      plannedDate: "2026-11-23",
    });
    expect(view.added[1]).toMatchObject({ title: "Sans module", moduleTitle: "" });
    expect(view.removed[0]).toMatchObject({
      title: "Regarder la vidéo 3",
      moduleTitle: "Bases du langage",
      plannedDate: null,
    });
    expect(view.moved[0]).toMatchObject({
      title: "Lire le chapitre 1",
      from: "2026-11-16",
      to: "2026-11-18",
    });
  });
});

describe("moduleForDate", () => {
  it("takes the first module of the week holding the date, skipped ones left out", () => {
    const skipping = program({
      weeks: [
        weekOut({
          modules: [moduleOut({ id: "skip", skipped: true }), moduleOut({ id: "m9", rank: 2 })],
        }),
      ],
    });
    expect(moduleForDate(skipping, "2026-11-19")).toBe("m9");
  });

  it("falls back to any module of the program for a date in an empty week", () => {
    const sparse = program({
      weeks: [weekOut(), weekOut({ id: "w2", rank: 2, start_date: "2026-11-23", modules: [] })],
    });
    expect(moduleForDate(sparse, "2026-11-25")).toBe("m1");
  });

  it("returns null when no module can take a task", () => {
    expect(moduleForDate(program({ weeks: [] }), "2026-11-19")).toBeNull();
  });
});

describe("toModuleLessons", () => {
  it("lists the lesson state of every planned module, in program order", () => {
    const lessons = toModuleLessons(program());
    expect(lessons).toEqual([
      {
        moduleId: "m1",
        moduleTitle: "Bases du langage",
        weekRank: 1,
        lessonId: "l1",
        status: "ready",
      },
      {
        moduleId: "m2",
        moduleTitle: "Fichiers CSV",
        weekRank: 2,
        lessonId: "l2",
        status: "generating",
      },
    ]);
  });

  it("leaves skipped modules out and keeps a module without lesson", () => {
    const view = toModuleLessons(
      program({
        weeks: [
          weekOut({
            modules: [
              moduleOut({ skipped: true }),
              moduleOut({ id: "m3", lesson_id: null, lesson_status: null }),
            ],
          }),
        ],
      }),
    );
    expect(view).toEqual([
      {
        moduleId: "m3",
        moduleTitle: "Bases du langage",
        weekRank: 1,
        lessonId: null,
        status: null,
      },
    ]);
  });
});
