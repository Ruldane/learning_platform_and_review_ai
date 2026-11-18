import { useSyncExternalStore } from "react";

/** Qui fait tourner les agents des parcours lancés depuis l'interface (en-tête `X-Tremplin-Run`). */
export const RUN_SOURCES = ["settings", "claude-code", "codex", "anthropic", "glm", "openai"] as const;
export type RunSource = (typeof RUN_SOURCES)[number];

export const RUN_HEADER = "X-Tremplin-Run";
const STORAGE_KEY = "tremplin.runSource";
const listeners = new Set<() => void>();

function isRunSource(value: unknown): value is RunSource {
  return typeof value === "string" && (RUN_SOURCES as readonly string[]).includes(value);
}

/** Le choix retenu par ce navigateur ; « selon mes réglages » sans stockage lisible. */
export function getRunSource(): RunSource {
  try {
    const saved = globalThis.localStorage?.getItem(STORAGE_KEY);
    return isRunSource(saved) ? saved : "settings";
  } catch {
    return "settings";
  }
}

export function setRunSource(value: RunSource): void {
  try {
    globalThis.localStorage?.setItem(STORAGE_KEY, value);
  } catch {
    // stockage refusé : le choix vaut jusqu'au rechargement seulement
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function useRunSource(): [RunSource, (value: RunSource) => void] {
  const value = useSyncExternalStore(subscribe, getRunSource, () => "settings" as const);
  return [value, setRunSource];
}
