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
 * Suit ce que January change sur le tableau. La référence est la scène affichée au départ (puis la
 * scène envoyée) ; `dirty` devient vrai dès qu'un élément en diffère.
 */
export function useBoardEdits(initial: readonly SceneElementLike[] | null) {
  const [sent, setSent] = useState<readonly SceneElementLike[] | null>(null);
  const first = useMemo(() => (initial ? snapshotOf(initial) : null), [initial]);
  const baseline = sent ?? first;
  const baselineRef = useRef(baseline);
  const current = useRef<readonly SceneElementLike[]>([]);
  const [dirty, setDirty] = useState(false);

  useEffect(() => {
    baselineRef.current = baseline;
  }, [baseline]);

  const onSceneChange = useCallback((elements: readonly SceneElementLike[]) => {
    current.current = snapshotOf(elements);
    const base = baselineRef.current;
    if (base) setDirty(signature(base) !== signature(current.current));
  }, []);

  const snapshot = useCallback(
    () => ({ before: baselineRef.current ?? [], after: current.current }),
    [],
  );

  /** Après l'envoi, ce qui est affiché devient la nouvelle référence. */
  const markSent = useCallback(() => {
    setSent(current.current);
    setDirty(false);
  }, []);

  return { dirty, onSceneChange, snapshot, markSent };
}
