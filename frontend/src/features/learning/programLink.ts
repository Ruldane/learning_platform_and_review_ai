import type { SessionEvent } from "@/shared/realtime/types";

const PROGRAM_BASE = "/apprendre/programme";
/** Une adresse de l'application : un chemin, jamais un autre site (`//hôte`, `https:`, `javascript:`). */
const INTERNAL = /^\/(?!\/)/;

/**
 * Le lien « Voir le programme » : dès que la session du programme annonce son `artifact.ready` de
 * genre `program` (son adresse si elle est interne, sinon construite avec l'identifiant), ou, après
 * un rechargement, avec le programme que l'objectif connaît déjà. `null` : pas encore prêt.
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
