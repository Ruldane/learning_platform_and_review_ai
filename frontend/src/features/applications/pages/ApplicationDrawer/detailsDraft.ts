import { toContactsIn, toContactView } from "../../toView";
import {
  isChannel,
  type ApplicationDetail,
  type ApplicationPatch,
  type ContactView,
} from "../../types";

/** A record's editable fields, as the form holds them (empty: field cleared). */
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

/** Is the form valid? `name`: empty company or job; `contact`: a contact without a name. */
export function problemOf(draft: DetailsDraft): "name" | "contact" | null {
  if (draft.company.trim() === "" || draft.title.trim() === "") return "name";
  return draft.contacts.some((contact) => contact.name.trim() === "") ? "contact" : null;
}

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

/** The text fields of `ApplicationPatch` (the enumerated channel is handled apart). */
type TextPatchKey =
  | "company"
  | "title"
  | "url"
  | "notes"
  | "next_action"
  | "next_action_on"
  | "applied_on"
  | "interview_on";

/** Only what changed since the record was read: a field left as is is not sent back. */
export function changesOf(draft: DetailsDraft, detail: ApplicationDetail): ApplicationPatch {
  const before = toDraft(detail);
  const patch: ApplicationPatch = {};
  const set = (key: TextPatchKey, field: TextKey, optional: boolean) => {
    if (draft[field].trim() === before[field].trim()) return;
    patch[key] = optional ? orNull(draft[field]) : draft[field].trim();
  };
  set("company", "company", false);
  set("title", "title", false);
  set("url", "url", true);
  if (draft.channel.trim() !== before.channel.trim()) {
    const channel = orNull(draft.channel);
    patch.channel = channel !== null && isChannel(channel) ? channel : null;
  }
  set("notes", "notes", true);
  set("next_action", "nextAction", true);
  set("next_action_on", "nextActionOn", true);
  set("applied_on", "appliedOn", true);
  set("interview_on", "interviewOn", true);
  const contacts = toContactsIn(draft.contacts);
  if (JSON.stringify(contacts) !== JSON.stringify(toContactsIn(before.contacts))) {
    patch.contacts = contacts;
  }
  return patch;
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
 * The record was re-read (a status, a note, a reminder, the save itself): each field that
 * January did not touch takes its new value (a date set by a status change, for
 * example); each field that was edited keeps its edit, saved or not.
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
