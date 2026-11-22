import { useId, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { mergeVoiceDraft, VoiceDraftControls } from "@/shared/voice";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";
import { InterruptTextField } from "./InterruptTextField";

interface InterruptFieldsProps {
  fields: InterruptField[];
  /** Texte saisi par champ : la carte le garde, pour que les options puissent l'envoyer aussi. */
  draft: Record<string, string>;
  onDraft: Dispatch<SetStateAction<Record<string, string>>>;
  disabled: boolean;
  /** Reçoit `{ answers: { <id du champ>: <texte> } }` : les champs vides sont omis. */
  onSubmit: (value: { answers: Record<string, string> }) => void;
  voice?: boolean;
}

/**
 * Cadrage à plusieurs questions : un champ par question (l'étiquette est la question). « Répondre »
 * envoie les réponses données ; il reste inactif tant que tous les champs sont vides ou qu'un
 * champ obligatoire manque. Le premier champ reçoit le focus.
 */
export function InterruptFields({
  fields,
  draft,
  onDraft,
  disabled,
  onSubmit,
  voice,
}: InterruptFieldsProps) {
  const prefix = useId();
  const answers = fieldAnswers(fields, draft);
  const missing = fields.some((field) => field.required && answers[field.id] === undefined);
  const ready = Object.keys(answers).length > 0 && !missing;
  const recorded = voice && !disabled && fields.length === 1 ? fields[0] : undefined;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled && ready) onSubmit({ answers });
  };

  return (
    <form onSubmit={submit} className="mt-2 flex flex-col gap-3">
      {fields.map((field, index) => (
        <InterruptTextField
          key={field.id}
          id={`${prefix}-${field.id}`}
          field={field}
          value={draft[field.id] ?? ""}
          disabled={disabled}
          focus={!disabled && index === 0}
          onChange={(value) => onDraft({ ...draft, [field.id]: value })}
        />
      ))}
      {recorded && (
        <VoiceDraftControls
          onDraft={(text) =>
            onDraft((values) => ({
              ...values,
              [recorded.id]: mergeVoiceDraft(values[recorded.id] ?? "", text, recorded.max_length),
            }))
          }
        />
      )}
      <div>
        <Button type="submit" disabled={disabled || !ready}>
          {t("session.interrupt.answer")}
        </Button>
      </div>
    </form>
  );
}
