import { useEffect, useRef, type RefObject } from "react";

/** Excalidraw mesure son conteneur à son tour : on lui laisse ce temps avant de cadrer. */
export const REFIT_DELAY_MS = 100;

/**
 * Cadre le contenu quand le canevas redevient visible. Un onglet masqué ramène son conteneur à une
 * taille nulle : tout cadrage fait à ce moment (nouvel état du Scribe, fenêtre redimensionnée) est
 * faux. Dès que la zone retrouve une taille, `refit` recadre. Une taille qui change sans être passée
 * par zéro ne recadre pas : January garde le zoom et la position qu'il a choisis.
 */
export function useRefitOnShow(frame: RefObject<HTMLElement | null>, refit: () => void): void {
  const latest = useRef(refit);
  useEffect(() => {
    latest.current = refit;
  });

  useEffect(() => {
    const element = frame.current;
    if (!element || typeof ResizeObserver === "undefined") return undefined;
    let hidden = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const observer = new ResizeObserver((entries) => {
      const box = entries.at(-1)?.contentRect;
      if (!box) return;
      const empty = box.width === 0 || box.height === 0;
      if (!empty && hidden) {
        clearTimeout(timer);
        timer = setTimeout(() => latest.current(), REFIT_DELAY_MS);
      }
      hidden = empty;
    });
    observer.observe(element);
    return () => {
      clearTimeout(timer);
      observer.disconnect();
    };
  }, [frame]);
}
