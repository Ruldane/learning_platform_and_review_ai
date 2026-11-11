import type { ItemEdit, ItemPatch, NewItem } from "../viewTypes";

export type NewKind = NewItem["kind"];
export type EditableLevel = NonNullable<ItemEdit["level"]>;

/** Brouillon du formulaire : les étiquettes restent une chaîne tant qu'on tape. */
export interface Draft {
  kind: NewKind;
  title: string;
  text: string;
  tags: string;
  level: EditableLevel;
}

export const NEW_KINDS: readonly NewKind[] = ["acquis", "decision", "offre"];

export function toDraft(initial: ItemEdit | null): Draft {
  return {
    kind: "acquis",
    title: initial?.title ?? "",
    text: initial?.text ?? "",
    tags: initial?.tags.join(", ") ?? "",
    level: initial?.level ?? "declare",
  };
}

/** Étiquettes séparées par des virgules : espaces retirés, vides et doublons écartés. */
export function parseTags(raw: string): string[] {
  const tags = raw.split(",").map((tag) => tag.trim());
  return tags.filter((tag, index) => tag !== "" && tags.indexOf(tag) === index);
}

/** Le niveau n'existe que pour un acquis : à la création, selon le type ; en édition, s'il est modifiable. */
export function showLevel(draft: Draft, chooseKind: boolean, initial: ItemEdit | null): boolean {
  return chooseKind ? draft.kind === "acquis" : initial?.level != null;
}

export const isValid = (draft: Draft, withText = true): boolean =>
  draft.title.trim() !== "" && (!withText || draft.text.trim() !== "");

const sameTags = (a: string[], b: string[]) =>
  a.length === b.length && a.every((v, i) => v === b[i]);

/** Seuls les champs modifiés partent au PATCH : un champ absent ne change rien côté back. */
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
