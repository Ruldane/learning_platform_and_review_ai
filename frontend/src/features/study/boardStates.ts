import { t } from "@/shared/i18n/t";
import type { SessionEvent } from "@/shared/realtime/types";
import type { BoardStateView } from "@/shared/session-ui";

/**
 * Les états du tableau d'une session d'étude : un par `board.update` du direct. Un état republié
 * (nœud rejoué, même `board_id` ou même étape) n'apparaît qu'une fois, dans sa dernière version.
 */
export function boardStatesFromEvents(events: readonly SessionEvent[]): BoardStateView[] {
  const states = new Map<string, BoardStateView>();
  for (const event of events) {
    if (event.type !== "board.update") continue;
    const { board_id, kind, title, step, mermaid } = event.payload;
    // Le Tuteur n'envoie pas de genre : c'est un schéma de la leçon, dessiné par lui (pas le Scribe).
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
