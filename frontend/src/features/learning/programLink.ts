import type { SessionEvent } from "@/shared/realtime/types";

const PROGRAM_BASE = "/learn/programs";
/** An app address: a path, never another site (`//host`, `https:`, `javascript:`). */
const INTERNAL = /^\/(?!\/)/;

/**
 * The « Voir le programme » link: as soon as the program session sends its `artifact.ready` of
 * kind `program` (its address if internal, otherwise built from the id), or, after
 * a reload, with the program the goal already knows. `null`: not ready yet.
 */
export function programLink(events: SessionEvent[], knownProgramId: string | null): string | null {
  for (let i = events.length - 1; i >= 0; i -= 1) {
    const event = events[i];
    if (event?.type !== "artifact.ready" || event.payload.kind !== "program") continue;
    const { url, artifact_id: id } = event.payload;
    return url && INTERNAL.test(url) ? url : `${PROGRAM_BASE}/${id}`;
  }
  return knownProgramId ? `${PROGRAM_BASE}/${knownProgramId}` : null;
}
