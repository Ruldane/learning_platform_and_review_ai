import { t } from "@/shared/i18n/t";
import { ContactList } from "../../components/ContactList";
import { DraftField } from "../../components/DraftField";
import { todayString } from "../../dates";
import { MANUAL_FIELDS, type ManualDraft, type ManualProblem } from "./manualDraft";

interface ManualFieldsProps {
  draft: ManualDraft;
  /** `name`: empty mandatory fields say so; `contact`: a contact without a name; `date`: a future
   * date. */
  problem: ManualProblem | null;
  onChange: (draft: ManualDraft) => void;
}

const textOf = (draft: ManualDraft, key: string): string => String(draft[key as keyof ManualDraft]);

/** The fields for manual creation, then the contacts. */
export function ManualFields({ draft, problem, onChange }: ManualFieldsProps) {
  return (
    <>
      <div className="grid gap-3 sm:grid-cols-2">
        {MANUAL_FIELDS.map((spec) => {
          const value = textOf(draft, spec.key);
          const missing = problem === "name" && spec.required && value.trim() === "";
          const future = problem === "date" && spec.key === "appliedOn";
          const error = missing
            ? t("applications.fields.required")
            : future
              ? t("applications.fields.futureDate")
              : undefined;
          return (
            <DraftField
              key={spec.key}
              spec={spec.key === "appliedOn" ? { ...spec, max: todayString() } : spec}
              value={value}
              error={error}
              onChange={(next) => onChange({ ...draft, [spec.key]: next })}
            />
          );
        })}
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
