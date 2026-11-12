import type { ExcalidrawElement } from "@excalidraw/excalidraw/element/types";
import { useEffect, useRef, type RefObject } from "react";
import type { BoardApi } from "./boardApi";
import { REFIT_DELAY_MS, useRefitOnShow } from "./useRefitOnShow";

/** Cadre toute la scène, en laissant la place aux barres d'outils d'Excalidraw (haut et bas). */
const FIT = {
  fitToViewport: true,
  viewportZoomFactor: 0.9,
  animate: false,
  canvasOffsets: { top: 72, bottom: 72, left: 16, right: 56 },
} as const;

interface Fitting {
  api: BoardApi | null;
  elements: readonly ExcalidrawElement[];
  /** La scène entière est affichée et stable : un dernier cadrage sur tout son contenu. */
  settled: boolean;
  /** Le conteneur du canevas, dont la taille passe par zéro quand l'onglet est masqué. */
  frame: RefObject<HTMLElement | null>;
  onReady: (api: BoardApi) => void;
}

/**
 * Tous les cadrages du canevas : à l'arrivée de l'API, une fois la scène stable, juste après la
 * première mesure du canevas (un état déjà vu n'a pas d'animation pour recadrer ensuite) et quand
 * un onglet masqué redevient visible.
 */
export function useFitting({ api, elements, settled, frame, onReady }: Fitting): void {
  const fitAll = () => api?.scrollToContent(undefined, FIT);
  useRefitOnShow(frame, fitAll);
  const onReadyRef = useRef(onReady);
  useEffect(() => {
    onReadyRef.current = onReady;
  });

  useEffect(() => {
    if (!api) return;
    onReadyRef.current(api);
    api.scrollToContent(elements as ExcalidrawElement[], FIT);
  }, [api, elements]);

  useEffect(() => {
    if (api && settled) api.scrollToContent(undefined, FIT);
  }, [api, settled]);

  // Le canevas se mesure juste après sa création : un cadrage fait à cet instant tombe à côté.
  useEffect(() => {
    if (!api) return undefined;
    const timer = setTimeout(() => api.scrollToContent(undefined, FIT), REFIT_DELAY_MS);
    return () => clearTimeout(timer);
  }, [api]);
}
