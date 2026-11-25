import { createContext, useSyncExternalStore } from "react";

/** Who runs the agents of runs launched from the interface (header `X-Tremplin-Run`). */
export const RUN_SOURCES = [
  "settings",
  "claude-code",
  "codex",
  "anthropic",
  "glm",
  "openai",
] as const;
export type RunSource = (typeof RUN_SOURCES)[number];

export const RUN_HEADER = "X-Tremplin-Run";
export const RunSourceAvailability = createContext<ReadonlySet<string> | undefined>(undefined);

/** An explicit "settings" value also overrides the global choice on this request. */
export function runSourceHeaders(source?: RunSource): Record<string, string> | undefined {
  return source === undefined ? undefined : { [RUN_HEADER]: source };
}

const STORAGE_KEY = "tremplin.runSource";
const listeners = new Set<() => void>();

export function isRunSource(value: unknown): value is RunSource {
  return typeof value === "string" && (RUN_SOURCES as readonly string[]).includes(value);
}

/** The choice kept by this browser; « selon mes réglages » when nothing readable is stored. */
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
    // storage refused: the choice lasts until reload only
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
