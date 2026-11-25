import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { SceneElementLike } from "../boardTypes";

/**
 * What counts as a change: the shape, its position (to the pixel), its text, its deletion.
 * Not the order (Excalidraw sorts labels after their shape), nor the version
 * (Excalidraw bumps it on each internal adjustment, such as a font loading…).
 * A linked label follows its shape: its own position does not count.
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
 * Light copy of the elements. Excalidraw edits its elements in place (a drag changes `x` and
 * `y` of the object already received): without a copy, the reference would track January's moves.
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
 * Tracks what January changes on the board. The reference is the last scene reported by the
 * read-only canvas (`reference`, the scene as Excalidraw adjusted it), failing that
 * the converter's, then the scene sent; `dirty` becomes true as soon as an element differs.
 */
export function useBoardEdits(initial: readonly SceneElementLike[] | null) {
  const first = useMemo(() => (initial ? snapshotOf(initial) : null), [initial]);
  const firstRef = useRef(first);
  /** Scene adjusted by Excalidraw, then scene sent: takes precedence over the converter's. */
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

  /** After sending, what is displayed becomes the new reference. */
  const markSent = useCallback(() => {
    shown.current = current.current;
    setDirty(false);
  }, []);

  return { dirty, onSceneChange, snapshot, markSent };
}
