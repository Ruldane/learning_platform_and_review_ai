import { t } from "@/shared/i18n/t";
import type { SceneElementLike } from "../boardTypes";

const MAX_LISTED = 5;
const MAX_TEXT_CHARS = 60;
const MOVE_THRESHOLD_PX = 1;

function alive(elements: readonly SceneElementLike[]): Map<string, SceneElementLike> {
  return new Map(elements.filter((el) => !el.isDeleted).map((el) => [el.id, el]));
}

function label(element: SceneElementLike): string {
  const flat = (element.text ?? "").replace(/\s+/g, " ").trim();
  return flat.length > MAX_TEXT_CHARS ? `${flat.slice(0, MAX_TEXT_CHARS)}…` : flat;
}

function quoted(labels: string[]): string {
  const shown = labels.slice(0, MAX_LISTED).map((text) => `« ${text} »`);
  if (labels.length > MAX_LISTED) shown.push("…");
  return shown.join(", ");
}

function texts(elements: Iterable<SceneElementLike>): string[] {
  return [...elements].filter((el) => el.type === "text" && label(el) !== "").map(label);
}

/** Shapes that move on their own: a label or arrow follows its shape. */
function isMovable(element: SceneElementLike): boolean {
  return element.type !== "text" && element.type !== "arrow" && element.type !== "line";
}

function moved(before: SceneElementLike, after: SceneElementLike): boolean {
  return (
    Math.abs(before.x - after.x) > MOVE_THRESHOLD_PX ||
    Math.abs(before.y - after.y) > MOVE_THRESHOLD_PX
  );
}

/**
 * Summarizes in one line what January changed on the board, for the message sent to the agents:
 * texts added, edited, deleted, and the number of shapes moved. Nothing changed: `""`.
 */
export function annotationNote(
  before: readonly SceneElementLike[],
  after: readonly SceneElementLike[],
): string {
  const was = alive(before);
  const now = alive(after);
  const added = texts([...now.values()].filter((el) => !was.has(el.id)));
  const removed = texts([...was.values()].filter((el) => !now.has(el.id)));
  const changed = texts(
    [...now.values()].filter((el) => {
      const old = was.get(el.id);
      return old !== undefined && el.type === "text" && label(old) !== label(el);
    }),
  );
  const movedCount = [...now.values()].filter((el) => {
    const old = was.get(el.id);
    return old !== undefined && isMovable(el) && moved(old, el);
  }).length;

  const parts: string[] = [];
  if (added.length) parts.push(t("session.board.note.added", { items: quoted(added) }));
  if (changed.length) parts.push(t("session.board.note.changed", { items: quoted(changed) }));
  if (removed.length) parts.push(t("session.board.note.removed", { items: quoted(removed) }));
  if (movedCount) parts.push(t("session.board.note.moved", { count: movedCount }));
  return parts.join(t("session.board.note.separator"));
}
