import type { FormEvent, ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { InlineError } from "@/shared/ui/states/InlineError";
import { Field } from "../../components/Field";

const MAX_SENTENCE = 1000;

interface SentenceFormProps {
  text: string;
  pending: boolean;
  error: string | null;
  onText: (text: string) => void;
  onSubmit: () => void;
  /** Ce qui s'affiche sous le champ : la saisie déjà ouverte à reprendre ou à annuler. */
  children?: ReactNode;
}

/** Le champ de la phrase (1 000 caractères au plus) et son bouton « Préparer la fiche ». */
export function SentenceForm({
  text,
  pending,
  error,
  onText,
  onSubmit,
  children,
}: SentenceFormProps) {
  const submit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };
  return (
    <form noValidate onSubmit={submit} className="flex flex-col gap-3">
      <Field
        label={t("applications.newPage.sentenceField")}
        hint={t("applications.newPage.sentenceHint")}
      >
        {(control) => (
          <textarea
            {...control}
            rows={3}
            maxLength={MAX_SENTENCE}
            value={text}
            placeholder={t("applications.newPage.sentencePlaceholder")}
            onChange={(event) => onText(event.target.value)}
            className={cn(fieldClass, "h-auto min-h-20 py-1.5")}
          />
        )}
      </Field>
      {error ? <InlineError message={error} /> : null}
      {children}
      <div>
        <Button type="submit" disabled={pending || text.trim() === ""}>
          {t(
            pending
              ? "applications.newPage.sentencePending"
              : "applications.newPage.sentenceAction",
          )}
        </Button>
      </div>
    </form>
  );
}
