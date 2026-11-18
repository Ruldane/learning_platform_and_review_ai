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
 * `true` sous 1024 px : les menus tiennent alors dans un panneau « Menu » et le panneau de gauche
 * se replie en une ligne sous la barre.
 */
export function useNarrowScreen(): boolean {
  return useSyncExternalStore(subscribe, snapshot, () => false);
}
