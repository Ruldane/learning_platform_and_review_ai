import { toContactsIn, toContactView } from "../../toView";
import type { ApplicationDetail, ApplicationPatch, ContactView } from "../../types";

/** Les champs modifiables d'une fiche, tels que le formulaire les tient (un vide : champ effacé). */
export interface DetailsDraft {
  company: string;
  title: string;
  url: string;
  channel: string;
  notes: string;
  nextAction: string;
  nextActionOn: string;
  appliedOn: string;
  interviewOn: string;
  contacts: ContactView[];
}

export type TextKey = Exclude<keyof DetailsDraft, "contacts">;

export function toDraft(detail: ApplicationDetail): DetailsDraft {
  return {
    company: detail.company,
    title: detail.title,
    url: detail.url ?? "",
    channel: detail.channel ?? "",
    notes: detail.notes ?? "",
    nextAction: detail.next_action ?? "",
    nextActionOn: detail.next_action_on ?? "",
    appliedOn: detail.applied_on ?? "",
    interviewOn: detail.interview_on ?? "",
    contacts: detail.contacts.map(toContactView),
  };
}

/** Le formulaire est-il valable ? `name` : entreprise ou poste vide ; `contact` : un contact sans nom. */
export function problemOf(draft: DetailsDraft): "name" | "contact" | null {
  if (draft.company.trim() === "" || draft.title.trim() === "") return "name";
  return draft.contacts.some((contact) => contact.name.trim() === "") ? "contact" : null;
}

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

/** Seulement ce qui a changé depuis la fiche lue : un champ laissé tel quel n'est pas renvoyé. */
export function changesOf(draft: DetailsDraft, detail: ApplicationDetail): ApplicationPatch {
  const before = toDraft(detail);
  const patch: Record<string, unknown> = {};
  const set = (key: string, field: TextKey, optional: boolean) => {
    if (draft[field].trim() === before[field].trim()) return;
    patch[key] = optional ? orNull(draft[field]) : draft[field].trim();
  };
  set("company", "company", false);
  set("title", "title", false);
  set("url", "url", true);
  set("channel", "channel", true);
  set("notes", "notes", true);
  set("next_action", "nextAction", true);
  set("next_action_on", "nextActionOn", true);
  set("applied_on", "appliedOn", true);
  set("interview_on", "interviewOn", true);
  const contacts = toContactsIn(draft.contacts);
  if (JSON.stringify(contacts) !== JSON.stringify(toContactsIn(before.contacts))) {
    patch.contacts = contacts;
  }
  return patch as ApplicationPatch;
}

const TEXT_KEYS: TextKey[] = [
  "company",
  "title",
  "url",
  "channel",
  "notes",
  "nextAction",
  "nextActionOn",
  "appliedOn",
  "interviewOn",
];

const sameContacts = (a: ContactView[], b: ContactView[]) =>
  JSON.stringify(toContactsIn(a)) === JSON.stringify(toContactsIn(b));

/**
 * La fiche a été relue (un statut, une note, une relance, la sauvegarde elle-même) : chaque champ que
 * January n'a pas touché prend sa nouvelle valeur (une date posée par un changement de statut, par
 * exemple), chaque champ qu'elle a retouché garde sa retouche, enregistrée ou non.
 */
export function rebase(
  draft: DetailsDraft,
  before: DetailsDraft,
  after: DetailsDraft,
): DetailsDraft {
  const next = { ...draft };
  for (const key of TEXT_KEYS) {
    if (draft[key] === before[key]) next[key] = after[key];
  }
  if (sameContacts(draft.contacts, before.contacts)) next.contacts = after.contacts;
  return next;
}
