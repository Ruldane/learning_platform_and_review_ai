import { describe, expect, it } from "vitest";
import { activityItem, briefOut } from "@/test/homeApi";
import type { ActivityItem, BriefOut } from "./types";
import { toActivityView, toBriefView } from "./toView";

describe("toBriefView", () => {
  it("maps the rubrics to the shapes the components read", () => {
    const view = toBriefView(briefOut() as unknown as BriefOut);
    expect(view.day).toBe("2026-11-16");
    expect(view.block).toEqual({
      moduleTitle: "SQL pour l'analyse",
      lessonTitle: "Les jointures SQL",
      minutes: 90,
      tasks: [
        { title: "Lire la leçon", minutes: 30 },
        { title: "Faire le quiz", minutes: 60 },
      ],
    });
    expect(view.reviews).toEqual({ queue: 12, remaining: 3 });
    expect(view.reminders.items[0]).toEqual({
      id: "r1",
      applicationId: "a1",
      company: "Société Fictive",
      title: "Data engineer",
      dueOn: "2026-11-16",
    });
    expect(view.offers[0]?.score).toBe(78);
    expect(view.week).toEqual({
      doneMinutes: 190,
      plannedMinutes: 300,
      streakDays: 4,
      tasksDone: 3,
      tasksTotal: 8,
    });
    expect(view.advice.status).toBe("ready");
  });

  it("keeps the empty rubrics empty", () => {
    const view = toBriefView(
      briefOut({
        block: null,
        week: null,
        resource: null,
        advice: null,
        advice_status: "pending",
        session_id: "s1",
      }) as unknown as BriefOut,
    );
    expect(view).toMatchObject({ block: null, week: null, resource: null, sessionId: "s1" });
    expect(view.advice).toEqual({ sentences: null, status: "pending" });
  });
});

describe("toActivityView", () => {
  it("turns the optional fields into null", () => {
    const { detail, link, ...rest } = activityItem("e1", "2026-11-16T10:00:00Z");
    void detail;
    void link;
    expect(toActivityView(rest as unknown as ActivityItem)).toMatchObject({
      id: "e1",
      detail: null,
      link: null,
    });
  });
});
