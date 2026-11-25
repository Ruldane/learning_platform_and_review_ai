import { t } from "@/shared/i18n/t";
import { Field } from "../Field";
import { ChoiceSelect, type ChoiceView } from "./ChoiceSelect";
import { TextControl } from "./TextControl";
import { CHANNEL_ORDER, STATUS_ORDER } from "../viewTypes";

/** Maximum length of the company and of the job title (server limit). */
export const NAME_MAX_LENGTH = 200;

export type FieldKind = "text" | "url" | "date" | "textarea" | "channel" | "status";

/** A record form field: its key, its label text (already in French) and its kind. */
export interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  hint?: string;
  maxLength?: number;
  /** Upper bound of a date field (`AAAA-MM-JJ`). */
  max?: string;
}

interface DraftFieldProps {
  spec: FieldSpec;
  value: string;
  /** The error text for this field (empty: none). */
  error?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  /** Replaces the list of a `channel` or `status` field (e.g. without the current status). */
  options?: ChoiceView[];
  onChange: (value: string) => void;
}

/** The statuses, in the tracking table's order, in French. */
export const statusChoices = (): ChoiceView[] =>
  STATUS_ORDER.map((value) => ({ value, label: t(`applications.status.${value}`) }));

/** The channels in French, preceded by « Non précisé ». */
const channelChoices = (): ChoiceView[] => [
  { value: "", label: t("applications.fields.channelNone") },
  ...CHANNEL_ORDER.map((value) => ({ value, label: t(`applications.channel.${value}`) })),
];

/** A record form field: text, link, date, textarea, channel or status. */
export function DraftField({
  spec,
  value,
  error,
  disabled,
  autoFocus,
  options,
  onChange,
}: DraftFieldProps) {
  const { kind } = spec;
  return (
    <Field label={spec.label} error={error} hint={spec.hint}>
      {(control) => {
        if (kind === "channel" || kind === "status") {
          const choices = options ?? (kind === "status" ? statusChoices() : channelChoices());
          return (
            <ChoiceSelect
              control={control}
              value={value}
              choices={choices}
              disabled={disabled}
              onChange={onChange}
            />
          );
        }
        return (
          <TextControl
            control={control}
            spec={spec}
            value={value}
            disabled={disabled}
            autoFocus={autoFocus}
            onChange={onChange}
          />
        );
      }}
    </Field>
  );
}
