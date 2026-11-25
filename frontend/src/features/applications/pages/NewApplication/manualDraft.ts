import { t } from "@/shared/i18n/t";
import { todayString } from "../../dates";
import { toContactsIn } from "../../toView";
import { isChannel, type ApplicationIn, type ContactView, type StatusView } from "../../types";
import { NAME_MAX_LENGTH, type FieldSpec } from "../../components/DraftField";

/** The fields for manual creation. */
export interface ManualDraft {
  company: string;
  title: string;
  url: string;
  status: StatusView;
  appliedOn: string;
  channel: string;
  notes: string;
  contacts: ContactView[];
}

export const EMPTY_DRAFT: ManualDraft = {
  company: "",
  title: "",
  url: "",
  status: "to_apply",
  appliedOn: "",
  channel: "",
  notes: "",
  contacts: [],
};

export type ManualKey = Exclude<keyof ManualDraft, "contacts">;

export const MANUAL_FIELDS: FieldSpec[] = [
  {
    key: "company",
    label: t("applications.fields.company"),
    kind: "text",
    required: true,
    maxLength: NAME_MAX_LENGTH,
  },
  {
    key: "title",
    label: t("applications.fields.title"),
    kind: "text",
    required: true,
    maxLength: NAME_MAX_LENGTH,
  },
  { key: "url", label: t("applications.fields.url"), kind: "url" },
  { key: "status", label: t("applications.fields.status"), kind: "status" },
  {
    key: "appliedOn",
    label: t("applications.fields.appliedOn"),
    kind: "date",
    hint: t("applications.newPage.appliedOnHint"),
  },
  { key: "channel", label: t("applications.fields.channel"), kind: "channel" },
  { key: "notes", label: t("applications.fields.notes"), kind: "textarea" },
];

export type ManualProblem = "name" | "contact" | "date";

/**
 * What prevents sending: `name` (company or job empty), `contact` (a contact without a name) or
 * `date` (an application date in the future, for a record already applied to).
 */
export function manualProblem(draft: ManualDraft): ManualProblem | null {
  if (draft.company.trim() === "" || draft.title.trim() === "") return "name";
  if (draft.contacts.some((contact) => contact.name.trim() === "")) return "contact";
  return draft.status !== "to_apply" && draft.appliedOn > todayString() ? "date" : null;
}

const orNull = (value: string) => (value.trim() === "" ? null : value.trim());

/** The chosen channel, or `null` (« Non précisé »). The menu only offers known ones. */
const channelOf = (value: string): ApplicationIn["channel"] => {
  const channel = value.trim();
  return isChannel(channel) ? channel : null;
};

/**
 * The body of `POST /applications`. `distinctFrom`: the near records January confirmed as
 * « autre poste ». An application date only makes sense for a record already applied to.
 */
export function toBody(draft: ManualDraft, distinctFrom: string[] = []): ApplicationIn {
  const body: ApplicationIn = {
    company: draft.company.trim(),
    title: draft.title.trim(),
    url: orNull(draft.url),
    status: draft.status,
    applied_on: draft.status === "to_apply" ? null : orNull(draft.appliedOn),
    channel: channelOf(draft.channel),
    notes: orNull(draft.notes),
    contacts: toContactsIn(draft.contacts),
  };
  if (distinctFrom.length > 0) body.distinct_from = distinctFrom;
  return body;
}
