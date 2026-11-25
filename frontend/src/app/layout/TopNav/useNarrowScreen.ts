import { useSyncExternalStore } from "react";

const QUERY = "(max-width: 1023px)";

function subscribe(onChange: () => void): () => void {
  if (typeof window.matchMedia !== "function") return () => undefined;
  const media = window.matchMedia(QUERY);
  media.addEventListener("change", onChange);
  return () => media.removeEventListener("change", onChange);
}

function snapshot(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia(QUERY).matches;
}

/**
 * `true` below 1024 px: menus then live in a « Menu » panel and the left panel
 * collapses into one line below the bar.
 */
export function useNarrowScreen(): boolean {
  return useSyncExternalStore(subscribe, snapshot, () => false);
}
