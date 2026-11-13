import { describe, expect, it } from "vitest";
import type { SessionEvent } from "@/shared/realtime/types";
import { boardStatesFromEvents } from "./boardStates";

const update = (seq: number, boardId: string | null, step: number, mermaid: string) =>
  ({
    id: `e${seq}`,
    session_id: "s1",
    seq,
    ts: `2026-11-17T10:00:0${seq}Z`,
    agent: "tutor",
    type: "board.update",
    payload: { board_id: boardId, step, kind: null, title: null, mermaid },
  }) as SessionEvent;

describe("boardStatesFromEvents", () => {
  it("builds one state per board and keeps the latest version of a republished one", () => {
    const states = boardStatesFromEvents([
      update(1, "b1", 1, "flowchart TD\n A-->B"),
      update(2, null, 2, "flowchart TD\n C-->D"),
      update(3, "b1", 1, "flowchart TD\n A-->C"),
    ]);
    expect(states.map((state) => state.id)).toEqual(["b1", "step-2"]);
    expect(states[0]).toMatchObject({
      mermaid: "flowchart TD\n A-->C",
      title: "Schéma de la leçon",
      kind: "lesson",
      author: "tutor",
      createdAt: "2026-11-17T10:00:01Z",
    });
  });

  it("ignores other events", () => {
    expect(boardStatesFromEvents([])).toEqual([]);
  });
});
