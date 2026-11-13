import { describe, expect, it } from "vitest";
import { compareOut, detailOut, graphOut, historyOut } from "@/test/skillsApi";
import { toCompareView, toDetailView, toGraphView, toHistoryView } from "./toView";

describe("skills toView", () => {
  it("renames the graph fields and keeps a null demand", () => {
    const view = toGraphView(graphOut() as never);
    expect(view.nodes[0]).toEqual({
      id: "s1",
      name: "HTML",
      domain: "web",
      level: "valide",
      demand: null,
      evidenceCount: 3,
    });
    expect(view.edges[0]).toEqual({ beforeId: "s1", afterId: "s2" });
    expect(view.domains).toEqual([{ domain: "web", score: 62 }]);
  });

  it("keeps an evidence without a date and a missing next action", () => {
    const view = toDetailView(detailOut({ next_action: null }) as never);
    expect(view.evidence[1]).toMatchObject({ label: "Programme web", at: null });
    expect(view.nextAction).toBeNull();
  });

  it("keeps a negative gap as it comes", () => {
    const view = toCompareView(compareOut() as never);
    expect(view.rows[0]).toMatchObject({ skillId: "s1", gap: -1, mine: "prouve" });
    expect(view.coverage).toBe(33);
  });

  it("renames the history points", () => {
    expect(toHistoryView(historyOut() as never)[1]).toEqual({
      weekStart: "2026-11-16",
      counts: { declare: 0, en_cours: 2, valide: 1, prouve: 0 },
      score: 58,
    });
  });
});
