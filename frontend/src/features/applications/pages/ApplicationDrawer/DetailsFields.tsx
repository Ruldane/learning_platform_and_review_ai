import { t } from "@/shared/i18n/t";
import { ContactList } from "../../components/ContactList";
import { DraftField, type FieldSpec } from "../../components/DraftField";
import type { DetailsDraft, TextKey } from "./detailsDraft";

const FIELDS: FieldSpec[] = [
  { key: "company", label: t("applications.fields.company"), kind: "text", required: true },
  { key: "title", label: t("applications.fields.title"), kind: "text", required: true },
  { key: "url", label: t("applications.fields.url"), kind: "url" },
  { key: "channel", label: t("applications.fields.channel"), kind: "channel" },
  { key: "appliedOn", label: t("applications.fields.appliedOn"), kind: "date" },
  { key: "interviewOn", label: t("applications.fields.interviewOn"), kind: "date" },
  { key: "nextAction", label: t("applications.fields.nextAction"), kind: "text" },
  { key: "nextActionOn", label: t("applications.fields.nextActionOn"), kind: "date" },
  { key: "notes", label: t("applications.fields.notes"), kind: "textarea" },
];

interface DetailsFieldsProps {
  draft: DetailsDraft;
  /** `name` : l'entreprise ou le poste vide le dit ; `contact` : un contact sans nom. */
  problem: "name" | "contact" | null;
  onChange: (draft: DetailsDraft) => void;
}

const isBlank = (draft: DetailsDraft, key: string) =>
  (key === "company" || key === "title") && draft[key].trim() === "";

/** Les champs modifiables de la fiche, puis ses contacts. */
export function DetailsFields({ draft, problem, onChange }: DetailsFieldsProps) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        {FIELDS.map((spec) => (
          <DraftField
            key={spec.key}
            spec={spec}
            value={draft[spec.key as TextKey]}
            error={
              problem === "name" && isBlank(draft, spec.key)
                ? t("applications.fields.required")
                : undefined
            }
            onChange={(value) => onChange({ ...draft, [spec.key]: value })}
          />
        ))}
      </div>
      <ContactList
        contacts={draft.contacts}
        onChange={(contacts) => onChange({ ...draft, contacts })}
      />
      {problem === "contact" ? (
        <p role="alert" className="text-sm text-destructive">
          {t("applications.drawer.contactNameRequired")}
        </p>
      ) : null}
    </>
  );
}
