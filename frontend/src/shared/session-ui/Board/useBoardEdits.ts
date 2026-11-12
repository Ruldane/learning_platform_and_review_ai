import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SceneElementLike } from "../boardTypes";

/**
 * Ce qui compte comme un changement : la forme, sa position (au pixel), son texte, sa suppression.
 * Ni l'ordre (Excalidraw range les étiquettes après leur forme), ni la version : Excalidraw la fait monter à chaque ajustement interne (police chargée…). Une
 * étiquette liée suit sa forme : sa position propre ne compte pas.
 */
function signature(elements: readonly SceneElementLike[]): string {
  return elements
    .map((el) => {
      const follows = el.type === "text" && el.containerId;
      const place = follows ? "" : `${Math.round(el.x)},${Math.round(el.y)}`;
      return `${el.id}:${place}:${el.isDeleted ?? false}:${el.text ?? ""}`;
    })
    .sort()
    .join("|");
}

/**
 * Copie légère des éléments. Excalidraw modifie ses éléments sur place (un glissement change `x` et
 * `y` de l'objet déjà reçu) : sans copie, la référence suivrait les gestes de January.
 */
function snapshotOf(elements: readonly SceneElementLike[]): SceneElementLike[] {
  return elements.map((el) => ({
    id: el.id,
    type: el.type,
    x: el.x,
    y: el.y,
    text: el.text,
    isDeleted: el.isDeleted,
    containerId: el.containerId,
  }));
}

/**
 * Suit ce que January change sur le tableau. La référence est la dernière scène signalée par le
 * canevas encore en lecture seule (`reference`, la scène telle qu'Excalidraw l'a ajustée), à défaut
 * celle du convertisseur, puis la scène envoyée ; `dirty` devient vrai dès qu'un élément en diffère.
 */
export function useBoardEdits(initial: readonly SceneElementLike[] | null) {
  const first = useMemo(() => (initial ? snapshotOf(initial) : null), [initial]);
  const firstRef = useRef(first);
  /** Scène ajustée par Excalidraw, puis scène envoyée : prime sur celle du convertisseur. */
  const shown = useRef<readonly SceneElementLike[] | null>(null);
  const current = useRef<readonly SceneElementLike[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    firstRef.current = first;
  }, [first]);

  const onSceneChange = useCallback((elements: readonly SceneElementLike[], reference = false) => {
    current.current = snapshotOf(elements);
    if (reference) {
      shown.current = current.current;
      setDirty(false);
      return;
    }
    const base = shown.current ?? firstRef.current;
    if (base) setDirty(signature(base) !== signature(current.current));
  }, []);

  const snapshot = useCallback(
    () => ({ before: shown.current ?? firstRef.current ?? [], after: current.current }),
    [],
  );

  /** Après l'envoi, ce qui est affiché devient la nouvelle référence. */
  const markSent = useCallback(() => {
    shown.current = current.current;
    setDirty(false);
  }, []);

  return { dirty, onSceneChange, snapshot, markSent };
}
