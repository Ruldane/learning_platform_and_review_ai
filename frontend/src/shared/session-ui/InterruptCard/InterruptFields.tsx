import { useId, type Dispatch, type FormEvent, type SetStateAction } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { mergeVoiceDraft, VoiceDraftControls } from "@/shared/voice";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";
import { InterruptTextField } from "./InterruptTextField";

interface InterruptFieldsProps {
  fields: InterruptField[];
  /** Text typed per field: the card keeps it, so the options can send it too. */
  draft: Record<string, string>;
  onDraft: Dispatch<SetStateAction<Record<string, string>>>;
  disabled: boolean;
  /** Receives `{ answers: { <field id>: <text> } }`: empty fields are omitted. */
  onSubmit: (value: { answers: Record<string, string> }) => void;
  voice?: boolean;
}

/**
 * Several questions: one field per question (the label is the question). « Répondre »
 * sends the answers given; it stays inactive while all fields are empty or a required
 * field is missing. The first field gets the focus.
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
