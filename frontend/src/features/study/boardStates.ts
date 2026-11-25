import { t } from "@/shared/i18n/t";
import type { SessionEvent } from "@/shared/realtime/types";
import type { BoardStateView } from "@/shared/session-ui";

/**
 * The states of a study session's board: one per `board.update` from the live feed. A
 * state republished (node replayed, same `board_id` or step) appears once, in its last version.
 */
export function boardStatesFromEvents(events: readonly SessionEvent[]): BoardStateView[] {
  const states = new Map<string, BoardStateView>();
  for (const event of events) {
    if (event.type !== "board.update") continue;
    const { board_id, kind, title, step, mermaid } = event.payload;
    // The Tutor sends no kind: it is a lesson diagram, drawn by it (not by the Scribe).
    const resolved = kind ?? "lesson";
    const id = board_id ?? `step-${step}`;
    states.set(id, {
      id,
      kind: resolved,
      title: title ?? t(`session.board.kinds.${resolved}`),
      step,
      mermaid,
      scene: null,
      author: "tutor",
      createdAt: states.get(id)?.createdAt ?? event.ts,
    });
  }
  return [...states.values()];
}
