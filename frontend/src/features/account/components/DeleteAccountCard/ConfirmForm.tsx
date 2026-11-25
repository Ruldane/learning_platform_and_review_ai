import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { FormFeedback } from "./FormFeedback";
import { WordField } from "./WordField";
import { useFocusOnFailure } from "./useFocusOnFailure";

/** What the backend answered: the text to show, and whether the refusal targets the confirmation
 * field. */
export interface DeleteFailure {
  message: string;
  field: boolean;
}

interface ConfirmFormProps {
  consentScope?: string;
  pending: boolean;
  /** A new object on each failure: focus moves to the message, even for a repeated failure. */
  failure: DeleteFailure | null;
  /** The warnings block, referenced by the field: it is announced on arrival. */
  explanationId: string;
  onDelete: (confirm: string) => void;
  /** The input changed: the displayed failure (and its mark on the field) disappears. */
  onEdit: () => void;
}

/**
 * The word to retype and the button. The button is enabled only for the exact word (`SUPPRIMER`,
 * without
 * trimming). During the call it stays reachable (`aria-disabled`, `aria-busy`) so that focus
 * does not drop, and the wait is announced; a failure receives focus, describes the field, and
 * disappears as soon as the input changes.
 */
export function ConfirmForm({
  consentScope,
  pending,
  failure,
  explanationId,
  onDelete,
  onEdit,
}: ConfirmFormProps) {
  const [draft, setDraft] = useState({ scope: consentScope, text: "" });
  if (draft.scope !== consentScope) setDraft({ scope: consentScope, text: "" });
  const typed = draft.scope === consentScope ? draft.text : "";
  const messageId = useId();
  const messageRef = useFocusOnFailure(failure);
  const exact = typed === t("account.delete.word");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (exact && !pending) onDelete(typed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-start gap-2">
      <WordField
        value={typed}
        invalid={failure?.field === true}
        describedBy={failure ? `${explanationId} ${messageId}` : explanationId}
        onChange={(value) => {
          setDraft({ scope: consentScope, text: value });
          onEdit();
        }}
      />
      <Button
        type="submit"
        variant="destructive"
        disabled={!exact}
        aria-disabled={pending || undefined}
        aria-busy={pending}
      >
        {pending ? t("account.delete.pending") : t("account.delete.submit")}
      </Button>
      <FormFeedback
        pending={pending}
        failure={failure}
        messageId={messageId}
        messageRef={messageRef}
      />
    </form>
  );
}
