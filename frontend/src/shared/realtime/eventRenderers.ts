import type { ComponentType } from "react";
import type { SessionEvent } from "./types";

/**
 * Render registry: event `type` → component. The feed (`DebateFeed`) asks for the component
 * of a generic event; a new type displays by registering its component, without touching
 * the feed. For a type without a component (`undefined`), the feed picks its own fallback.
 */
export type EventRenderer = ComponentType<{ event: SessionEvent }>;

const renderers = new Map<SessionEvent["type"], EventRenderer>();

/** Registers (or replaces) a type's component; returns what is needed to remove it. */
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
