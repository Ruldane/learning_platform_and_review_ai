import type { ComponentType } from "react";
import type { SessionEvent } from "./types";

/**
 * Registre de rendu : `type` d'événement → composant. Le fil (`DebateFeed`) demande le composant
 * d'un événement générique ; un nouveau type s'affiche en enregistrant son composant, sans toucher
 * au fil. Pour un type sans composant (`undefined`), le fil choisit son repli.
 */
export type EventRenderer = ComponentType<{ event: SessionEvent }>;

const renderers = new Map<SessionEvent["type"], EventRenderer>();

/** Enregistre (ou remplace) le composant d'un type ; renvoie de quoi le retirer. */
export function registerEventRenderer(
  type: SessionEvent["type"],
  renderer: EventRenderer,
): () => void {
  renderers.set(type, renderer);
  return () => {
    if (renderers.get(type) === renderer) renderers.delete(type);
  };
}

export function getEventRenderer(type: SessionEvent["type"]): EventRenderer | undefined {
  return renderers.get(type);
}
