import type { KeyboardCoordinateGetter } from "@dnd-kit/core";

const STEP: Record<string, 1 | -1> = { ArrowRight: 1, ArrowLeft: -1 };

/**
 * Clavier du glisser-déposer : une flèche gauche ou droite amène la tâche au centre du jour voisin
 * (le défaut de dnd-kit avance de quelques pixels). Les flèches haut et bas sont ignorées.
 */
export const columnKeyboardCoordinates: KeyboardCoordinateGetter = (
  event,
  { currentCoordinates, context: { collisionRect, droppableRects, droppableContainers } },
) => {
  const direction = STEP[event.code];
  if (!direction || !collisionRect) return undefined;
  event.preventDefault();
  const here = collisionRect.left + collisionRect.width / 2;
  const target = droppableContainers
    .getEnabled()
    .map((container) => droppableRects.get(container.id))
    .filter((rect) => rect !== undefined)
    .map((rect) => ({ rect, centre: rect.left + rect.width / 2 }))
    .filter(({ centre }) => (centre - here) * direction > 1)
    .sort((a, b) => (a.centre - b.centre) * direction)[0];
  if (!target) return undefined;
  const x = target.rect.left + (target.rect.width - collisionRect.width) / 2;
  return { x, y: currentCoordinates.y };
};
