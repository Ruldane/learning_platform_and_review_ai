import { useId, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { cn } from "@/shared/lib/utils";
import { fieldClass } from "@/shared/ui/fieldClass";
import { fieldAnswers, type InterruptField } from "./fieldAnswers";

interface InterruptFieldsProps {
  fields: InterruptField[];
  /** Texte saisi par champ : la carte le garde, pour que les options puissent l'envoyer aussi. */
  draft: Record<string, string>;
  onDraft: (draft: Record<string, string>) => void;
  disabled: boolean;
  /** Reçoit `{ answers: { <id du champ>: <texte> } }` : les champs vides sont omis. */
  onSubmit: (value: { answers: Record<string, string> }) => void;
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
}: InterruptFieldsProps) {
  const prefix = useId();
  const answers = fieldAnswers(fields, draft);
  const missing = fields.some((field) => field.required && answers[field.id] === undefined);
  const ready = Object.keys(answers).length > 0 && !missing;

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!disabled && ready) onSubmit({ answers });
  };

  return (
    <form onSubmit={submit} className="mt-2 flex flex-col gap-3">
      {fields.map((field, index) => (
        <div key={field.id} className="flex flex-col gap-1">
          <label htmlFor={`${prefix}-${field.id}`} className="text-sm font-medium">
            {field.label}
          </label>
          <textarea
            id={`${prefix}-${field.id}`}
            rows={2}
            value={draft[field.id] ?? ""}
            maxLength={field.max_length}
            required={field.required}
            disabled={disabled}
            autoFocus={!disabled && index === 0}
            aria-describedby={field.required ? `${prefix}-${field.id}-req` : undefined}
            onChange={(event) => onDraft({ ...draft, [field.id]: event.target.value })}
            className={cn(fieldClass, "h-auto min-h-16 py-1.5")}
          />
          {field.required ? (
            <span id={`${prefix}-${field.id}-req`} className="text-xs text-muted-foreground">
              {t("session.interrupt.required")}
            </span>
          ) : null}
        </div>
      ))}
      <div>
        <Button type="submit" disabled={disabled || !ready}>
          {t("session.interrupt.answer")}
        </Button>
      </div>
    </form>
  );
}
