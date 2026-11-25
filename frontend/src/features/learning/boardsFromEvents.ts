import { t } from "@/shared/i18n/t";
import type { EventOf, SessionEvent } from "@/shared/realtime/types";
import type { BoardStateView } from "@/shared/session-ui";

type BoardUpdate = EventOf<"board.update">;

/** The same state? By `board_id` when the event carries one, otherwise by step (and known type). */
function sameState(state: BoardStateView, payload: BoardUpdate["payload"]): boolean {
  if (payload.board_id !== null) return state.id === payload.board_id;
  return (
    state.author === "scribe" &&
    state.step === payload.step &&
    (payload.kind === null || state.kind === payload.kind)
  );
}

function liveState(event: BoardUpdate): BoardStateView {
  const { board_id, kind, title, step, mermaid } = event.payload;
  const resolved = kind ?? "domain_map";
  return {
    id: board_id ?? `step-${step}`,
    kind: resolved,
    title: title ?? t(`session.board.kinds.${resolved}`),
    step,
    mermaid,
    scene: null,
    author: "scribe",
    createdAt: event.ts,
  };
}

/** The Scribe's state as the live feed redraws it; what is saved (scene, date) stays. */
function refresh(state: BoardStateView, live: BoardStateView): BoardStateView {
  return {
    ...state,
    kind: live.kind,
    title: live.title,
    step: live.step,
    mermaid: live.mermaid,
  };
}

/**
 * A Council's board states: those of `GET /goals/{id}/boards`, then each `board.update`
 * from the live feed. A state appears once, even if a replayed node republishes it (`board_id`, or
 * else the step): the Scribe's latest version wins; a January state is never replaced.
 */
export function boardsFromEvents(
  saved: BoardStateView[],
  events: SessionEvent[],
): BoardStateView[] {
  const states = [...saved];
  for (const event of events) {
    if (event.type !== "board.update") continue;
    const live = liveState(event);
    const index = states.findIndex((state) => sameState(state, event.payload));
    const known = index >= 0 ? states[index] : undefined;
    if (known === undefined) states.push(live);
    else if (known.author === "scribe") states[index] = refresh(known, live);
  }
  return states;
}
