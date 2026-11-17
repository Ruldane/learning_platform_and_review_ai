import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { fieldClass } from "@/shared/ui/fieldClass";
import { useFocusOnFailure } from "./useFocusOnFailure";

/** Ce qu'a répondu le back : le texte à montrer, et si le refus vise le champ de confirmation. */
export interface DeleteFailure {
  message: string;
  field: boolean;
}

interface ConfirmFormProps {
  pending: boolean;
  /** Un nouvel objet à chaque échec : le focus passe au message même pour un échec répété. */
  failure: DeleteFailure | null;
  onDelete: (confirm: string) => void;
}

/**
 * Le mot à retaper et le bouton. Le bouton ne s'active que sur le mot exact (`SUPPRIMER`, sans
 * rognage). Pendant l'appel il reste atteignable (`aria-disabled`, `aria-busy`) pour que le focus
 * ne tombe pas ; un échec reçoit le focus et décrit le champ.
 */
export function ConfirmForm({ pending, failure, onDelete }: ConfirmFormProps) {
  const [typed, setTyped] = useState("");
  const inputId = useId();
  const messageId = useId();
  const messageRef = useFocusOnFailure(failure);
  const exact = typed === t("account.delete.word");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (exact && !pending) onDelete(typed);
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-start gap-2">
      <label htmlFor={inputId} className="text-sm font-medium">
        {t("account.delete.label")}
      </label>
      <input
        id={inputId}
        type="text"
        value={typed}
        onChange={(event) => setTyped(event.target.value)}
        autoComplete="off"
        autoCapitalize="off"
        spellCheck={false}
        aria-invalid={failure?.field ? true : undefined}
        aria-describedby={failure ? messageId : undefined}
        className={`${fieldClass} max-w-xs`}
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
      {failure ? (
        <p
          id={messageId}
          ref={messageRef}
          role="alert"
          tabIndex={-1}
          className="rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive outline-none focus-visible:ring-3 focus-visible:ring-ring"
        >
          {failure.message}
        </p>
      ) : null}
    </form>
  );
}
