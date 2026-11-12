import { describe, expect, it } from "vitest";
import { councilEvents } from "@/test/councilEvents";
import { councilStage } from "./councilStage";

describe("councilStage", () => {
  it("starts at the framing, with no round, and counts round 1 in the total (1 + 3 by default)", () => {
    expect(councilStage([], false)).toEqual({ stage: "framing", round: 0, rounds: 4 });
  });

  it("stays in framing while the questions wait for the answers", () => {
    const e = councilEvents();
    expect(councilStage([e.interrupt("framing", "i1")], false).stage).toBe("framing");
  });

  it("moves to research on a web tool or a source", () => {
    const e = councilEvents();
    const framing = [e.interrupt("framing", "i1"), e.toolCalled("c1", "web_search")];
    expect(councilStage(framing, false).stage).toBe("research");
    expect(councilStage([e.sourceFound()], false).stage).toBe("research");
  });

  it("ignores a memory tool and does not leave the framing for it", () => {
    const e = councilEvents();
    expect(councilStage([e.toolCalled("c1", "memory_search")], false).stage).toBe("framing");
  });

  it("follows the round of the « tour-n » messages", () => {
    const e = councilEvents();
    const events = [
      e.toolCalled("c1", "web_search"),
      e.message("moderator-tour-1", "Tour 1 : ..."),
      e.message("moderator-tour-2", "Tour 2 : ..."),
    ];
    expect(councilStage(events, false)).toEqual({ stage: "debate", round: 2, rounds: 4 });
  });

  it("does not go back to research when a debater reads the web during the debate", () => {
    const e = councilEvents();
    const events = [e.message("moderator-tour-1", "Tour 1"), e.toolCalled("c9", "web_read")];
    expect(councilStage(events, false).stage).toBe("debate");
  });

  it("announces 1 + debate_rounds rounds, capped at 8, never fewer than the round in progress", () => {
    const e = councilEvents();
    const tour = (n: number) => [e.message(`moderator-tour-${n}`, `Tour ${n}`)];
    expect(councilStage(tour(3), false, 3)).toMatchObject({ round: 3, rounds: 4 });
    expect(councilStage(tour(4), false, 3)).toMatchObject({ round: 4, rounds: 4 });
    expect(councilStage(tour(2), false, 1)).toMatchObject({ round: 2, rounds: 2 });
    expect(councilStage(tour(1), false, 5)).toMatchObject({ round: 1, rounds: 6 });
    expect(councilStage([], false, 9)).toMatchObject({ rounds: 8 });
    // « Un tour de plus » : le tour ajouté relève le total.
    expect(councilStage(tour(5), false, 3)).toMatchObject({ round: 5, rounds: 5 });
  });

  it("reaches the proposals with proposal.ready or the choice interrupt", () => {
    const e = councilEvents();
    const debate = [e.message("moderator-tour-3", "Tour 3")];
    expect(councilStage([...debate, e.proposalReady("p1", "A")], false).stage).toBe("proposals");
    expect(councilStage([...debate, e.interrupt("choose_path", "i2")], false)).toMatchObject({
      stage: "proposals",
      round: 3,
    });
  });

  it("goes back to the debate when another round is asked", () => {
    const e = councilEvents();
    const events = [
      e.message("moderator-tour-3", "Tour 3"),
      e.proposalReady("p1", "A"),
      e.interrupt("choose_path", "i2"),
      e.message("moderator-tour-4", "Tour 4"),
    ];
    expect(councilStage(events, false)).toMatchObject({ stage: "debate", round: 4 });
  });

  it("goes to the program once the choice is announced or a program is known", () => {
    const e = councilEvents();
    const chosen = [e.proposalReady("p1", "A"), e.message("moderator-choix", "Parcours choisi")];
    expect(councilStage(chosen, false).stage).toBe("program");
    expect(councilStage([e.proposalReady("p2", "B")], true).stage).toBe("program");
  });
});
