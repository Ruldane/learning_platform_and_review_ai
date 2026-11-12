import { describe, expect, it } from "vitest";
import { boardOut, goalOut, proposalOut } from "@/test/councilApi";
import { newestFirst, toBoardView, toGoalRow, toProposalView } from "./toView";
import type { BoardOut, GoalOut, ProposalOut } from "./types";

describe("toView", () => {
  it("converts a goal to a row", () => {
    const goal = goalOut({ deadline: "2027-01-31", program_id: "pr1", status: "planned" });
    expect(toGoalRow(goal as GoalOut)).toEqual({
      id: "g1",
      text: "Devenir ingénieure data",
      targetRole: "Data engineer",
      deadline: "2027-01-31",
      weeklyHours: 8,
      status: "planned",
      programId: "pr1",
    });
  });

  it("sorts goals from the newest to the oldest, without changing the input", () => {
    const goals = [
      goalOut({ id: "a", created_at: "2026-11-01T10:00:00Z" }),
      goalOut({ id: "b", created_at: "2026-11-09T10:00:00Z" }),
    ] as GoalOut[];
    expect(newestFirst(goals).map((g) => g.id)).toEqual(["b", "a"]);
    expect(goals.map((g) => g.id)).toEqual(["a", "b"]);
  });

  it("converts a proposal", () => {
    const proposal = proposalOut("p1", 2, { board_id: "b3", chosen: true }) as ProposalOut;
    expect(toProposalView(proposal)).toEqual({
      id: "p1",
      rank: 2,
      name: "Parcours 2",
      promise: "Une promesse.",
      durationWeeks: 8,
      weeklyHours: 6,
      skills: ["Python"],
      finalProject: "Un projet",
      tradeoffs: ["Un compromis"],
      boardId: "b3",
      chosen: true,
    });
  });

  it("converts a board state, naming an untitled one after its kind", () => {
    const named = toBoardView(boardOut("b1") as BoardOut);
    expect(named).toMatchObject({ id: "b1", kind: "domain_map", step: 1, author: "scribe" });
    expect(named.createdAt).toBe("2026-11-12T10:00:00Z");
    const untitled = toBoardView(boardOut("b2", { title: "", kind: "timeline" }) as BoardOut);
    expect(untitled.title).toBe("Frise du parcours");
  });
});
