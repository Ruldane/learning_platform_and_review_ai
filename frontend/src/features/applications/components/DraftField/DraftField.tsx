import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";
import { Field } from "../Field";
import { ChoiceSelect, type ChoiceView } from "./ChoiceSelect";
import { CHANNEL_ORDER, STATUS_ORDER } from "../viewTypes";

export type FieldKind = "text" | "url" | "date" | "textarea" | "channel" | "status";

/** Un champ de formulaire de fiche : sa clé, son texte d'étiquette (déjà en français) et sa nature. */
export interface FieldSpec {
  key: string;
  label: string;
  kind: FieldKind;
  required?: boolean;
  hint?: string;
  maxLength?: number;
}

interface DraftFieldProps {
  spec: FieldSpec;
  value: string;
  /** Le texte d'une erreur sur ce champ (vide : aucun). */
  error?: string;
  disabled?: boolean;
  autoFocus?: boolean;
  /** Remplace la liste d'un champ `channel` ou `status` (ex. sans le statut actuel). */
  options?: ChoiceView[];
  onChange: (value: string) => void;
}

/** Les statuts, dans l'ordre du tableau de suivi, en français. */
export const statusChoices = (): ChoiceView[] =>
  STATUS_ORDER.map((value) => ({ value, label: t(`applications.status.${value}`) }));

/** Les canaux en français, précédés de « Non précisé ». */
const channelChoices = (): ChoiceView[] => [
  { value: "", label: t("applications.fields.channelNone") },
  ...CHANNEL_ORDER.map((value) => ({ value, label: t(`applications.channel.${value}`) })),
];

/** Un champ de formulaire de fiche : texte, lien, date, zone de texte, canal ou statut. */
export function DraftField({
  spec,
  value,
  error,
  disabled,
  autoFocus,
  options,
  onChange,
}: DraftFieldProps) {
  const { kind, maxLength, required } = spec;
  const common = { value, disabled, autoFocus, required, maxLength };
  const change = (event: { target: { value: string } }) => onChange(event.target.value);
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
        if (kind === "textarea") {
          return (
            <textarea
              {...control}
              {...common}
              rows={3}
              maxLength={maxLength ?? 2000}
              onChange={change}
              className={cn(fieldClass, "h-auto min-h-16 py-1.5")}
            />
          );
        }
        return (
          <input {...control} {...common} type={kind} onChange={change} className={fieldClass} />
        );
      }}
    </Field>
  );
}
