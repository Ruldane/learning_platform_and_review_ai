import type { ItemEdit, ItemPatch, NewItem } from "../viewTypes";

export type NewKind = NewItem["kind"];
export type EditableLevel = NonNullable<ItemEdit["level"]>;

/** Form draft: the labels stay a string while typing. */
export interface Draft {
  kind: NewKind;
  title: string;
  text: string;
  tags: string;
  level: EditableLevel;
}

export const NEW_KINDS: readonly NewKind[] = ["skill", "decision", "posting"];

export function toDraft(initial: ItemEdit | null): Draft {
  return {
    kind: "skill",
    title: initial?.title ?? "",
    text: initial?.text ?? "",
    tags: initial?.tags.join(", ") ?? "",
    level: initial?.level ?? "declared",
  };
}

/** Labels separated by commas: spaces trimmed, empty and duplicate ones dropped. */
export function parseTags(raw: string): string[] {
  const tags = raw.split(",").map((tag) => tag.trim());
  return tags.filter((tag, index) => tag !== "" && tags.indexOf(tag) === index);
}

/** The level exists only for an acquired item: on creation by type; on edit, if it is editable. */
export function showLevel(draft: Draft, chooseKind: boolean, initial: ItemEdit | null): boolean {
  return chooseKind ? draft.kind === "skill" : initial?.level != null;
}

export const isValid = (draft: Draft, withText = true): boolean =>
  draft.title.trim() !== "" && (!withText || draft.text.trim() !== "");

const sameTags = (a: string[], b: string[]) =>
  a.length === b.length && a.every((v, i) => v === b[i]);

/** Only the changed fields go in the PATCH: a missing field changes nothing on the back end. */
function changedFields(edit: ItemEdit, initial: ItemEdit | null, withText: boolean): ItemPatch {
  const patch: ItemPatch = {};
  if (edit.title !== initial?.title) patch.title = edit.title;
  if (withText && edit.text !== initial?.text) patch.text = edit.text;
  if (!sameTags(edit.tags, initial?.tags ?? [])) patch.tags = edit.tags;
  if (edit.level !== null && edit.level !== initial?.level) patch.level = edit.level;
  return patch;
}

export function buildValue(
  draft: Draft,
  chooseKind: boolean,
  initial: ItemEdit | null,
  withText = true,
): ItemPatch | NewItem {
  const edit: ItemEdit = {
    title: draft.title.trim(),
    text: draft.text.trim(),
    tags: parseTags(draft.tags),
    level: showLevel(draft, chooseKind, initial) ? draft.level : null,
  };
  return chooseKind ? { ...edit, kind: draft.kind } : changedFields(edit, initial, withText);
}
