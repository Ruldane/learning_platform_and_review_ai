import type { ItemEdit, NewItem } from "../viewTypes";

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

export const isValid = (draft: Draft): boolean =>
  draft.title.trim() !== "" && draft.text.trim() !== "";

export function buildValue(
  draft: Draft,
  chooseKind: boolean,
  initial: ItemEdit | null,
): ItemEdit | NewItem {
  const edit: ItemEdit = {
    title: draft.title.trim(),
    text: draft.text.trim(),
    tags: parseTags(draft.tags),
    level: showLevel(draft, chooseKind, initial) ? draft.level : null,
  };
  return chooseKind ? { ...edit, kind: draft.kind } : edit;
}
