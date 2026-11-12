import { t } from "@/shared/i18n/t";
import type { EventOf, SessionEvent } from "@/shared/realtime/types";
import type { BoardStateView } from "@/shared/session-ui";

type BoardUpdate = EventOf<"board.update">;

/** Le même état ? Par `board_id` quand l'événement en porte un, sinon par étape (et type connu). */
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

/** L'état du Scribe tel que le direct le redessine ; ce qui est enregistré (scène, date) reste. */
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
 * Les états du tableau d'un Conseil : ceux de `GET /goals/{id}/boards`, puis chaque `board.update`
 * du direct. Un état n'apparaît qu'une fois, même si un nœud rejoué le republie (`board_id`, à
 * défaut l'étape) : la dernière version du Scribe l'emporte, un état de January n'est jamais remplacé.
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
