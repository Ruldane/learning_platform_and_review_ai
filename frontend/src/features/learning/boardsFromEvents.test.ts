import { describe, expect, it } from "vitest";
import type { BoardStateView } from "@/shared/session-ui";
import { councilEvents } from "@/test/councilEvents";
import { boardsFromEvents } from "./boardsFromEvents";

const saved = (over: Partial<BoardStateView> = {}): BoardStateView => ({
  id: "b1",
  kind: "domain_map",
  title: "Carte du domaine",
  step: 1,
  mermaid: "flowchart TD\n  A --> B",
  scene: null,
  author: "scribe",
  createdAt: "2026-11-12T10:00:00Z",
  ...over,
});

describe("boardsFromEvents", () => {
  it("starts from the saved states", () => {
    expect(boardsFromEvents([saved()], [])).toEqual([saved()]);
  });

  it("adds the states drawn live", () => {
    const e = councilEvents();
    const result = boardsFromEvents(
      [],
      [
        e.boardUpdate("b1", 1),
        e.boardUpdate("b2", 2, { kind: "prerequisites", title: "Prérequis" }),
      ],
    );
    expect(result.map((s) => [s.id, s.kind, s.step, s.author])).toEqual([
      ["b1", "domain_map", 1, "scribe"],
      ["b2", "prerequisites", 2, "scribe"],
    ]);
  });

  it("does not duplicate a state that is both saved and live", () => {
    const e = councilEvents();
    expect(boardsFromEvents([saved()], [e.boardUpdate("b1", 1)])).toHaveLength(1);
  });

  it("lets the last live version of a Scribe state win, keeping what was saved", () => {
    const e = councilEvents();
    const result = boardsFromEvents(
      [saved({ createdAt: "2026-11-12T09:00:00Z" })],
      [e.boardUpdate("b1", 1, { mermaid: "flowchart TD\n  X --> Y" })],
    );
    expect(result).toHaveLength(1);
    expect(result[0]).toMatchObject({
      mermaid: "flowchart TD\n  X --> Y",
      createdAt: "2026-11-12T09:00:00Z",
    });
  });

  it("never overwrites a state edited by January", () => {
    const e = councilEvents();
    const mine = saved({ id: "b9", author: "user", scene: { elements: [] }, step: 1 });
    const result = boardsFromEvents([saved(), mine], [e.boardUpdate("b9", 1)]);
    expect(result.find((s) => s.id === "b9")).toEqual(mine);
    expect(result).toHaveLength(2);
  });

  it("collapses a replayed event published twice with the same board_id", () => {
    const e = councilEvents();
    expect(boardsFromEvents([], [e.boardUpdate("b1", 1), e.boardUpdate("b1", 1)])).toHaveLength(1);
  });

  it("identifies an event without board_id by its step", () => {
    const e = councilEvents();
    const hidden = { kind: null, title: null };
    const result = boardsFromEvents(
      [],
      [
        e.boardUpdate(null, 1, hidden),
        e.boardUpdate(null, 1, hidden),
        e.boardUpdate(null, 2, hidden),
      ],
    );
    expect(result.map((s) => s.step)).toEqual([1, 2]);
    expect(result[0]?.title).toBe("Carte du domaine");
  });

  it("ignores events that are not board updates", () => {
    const e = councilEvents();
    expect(boardsFromEvents([], [e.message("m", "x"), e.cost()])).toEqual([]);
  });
});
