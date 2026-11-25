import { t } from "@/shared/i18n/t";
import { DraftField, type FieldKind, type FieldSpec } from "../DraftField";
import { todayString } from "../format";
import type { ConfirmationFieldView, ConfirmationView } from "../viewTypes";

/** The kind of a field: status, channel, date and notes have their own control, the rest is
 * text. */
const KINDS: Record<string, FieldKind> = {
  status: "status",
  channel: "channel",
  applied_on: "date",
  notes: "textarea",
};

function specOf(field: ConfirmationFieldView, value: string): FieldSpec {
  const todayHint = field.id === "applied_on" && value === "";
  return {
    key: field.id,
    label: field.label,
    kind: KINDS[field.id] ?? "text",
    required: field.required,
    maxLength: field.maxLength,
    max: field.id === "applied_on" ? todayString() : undefined,
    hint: todayHint ? t("applications.confirm.todayHint") : undefined,
  };
}

interface ConfirmationFieldsProps {
  confirmation: ConfirmationView;
  values: Record<string, string>;
  disabled: boolean;
  /** A contact role is given without a name: the name field says so. */
  roleWithoutName: boolean;
  onChange: (id: string, value: string) => void;
}

/** The fields of the record read: one field per piece of information, already filled in, in the
 * server's order. */
export function ConfirmationFields({
  confirmation,
  values,
  disabled,
  roleWithoutName,
  onChange,
}: ConfirmationFieldsProps) {
  return (
    <div
      role="group"
      aria-label={t("applications.confirm.label")}
      className="grid gap-3 sm:grid-cols-2"
    >
      {confirmation.fields.map((field, index) => (
        <DraftField
          key={field.id}
          spec={specOf(field, values[field.id] ?? "")}
          error={
            roleWithoutName && field.id === "contact_name"
              ? t("applications.confirm.roleNeedsName")
              : undefined
          }
          value={values[field.id] ?? ""}
          disabled={disabled}
          autoFocus={!disabled && index === 0}
          onChange={(value) => onChange(field.id, value)}
        />
      ))}
    </div>
  );
}
