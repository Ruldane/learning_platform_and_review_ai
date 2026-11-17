import { useId, useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { FormFeedback } from "./FormFeedback";
import { WordField } from "./WordField";
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
  /** Le bloc d'avertissements, cité par le champ : on l'entend en y arrivant. */
  explanationId: string;
  onDelete: (confirm: string) => void;
  /** La saisie a changé : l'échec affiché (et sa marque sur le champ) disparaît. */
  onEdit: () => void;
}

/**
 * Le mot à retaper et le bouton. Le bouton ne s'active que sur le mot exact (`SUPPRIMER`, sans
 * rognage). Pendant l'appel il reste atteignable (`aria-disabled`, `aria-busy`) pour que le focus
 * ne tombe pas, et l'attente est annoncée ; un échec reçoit le focus, décrit le champ, et
 * disparaît dès que la saisie change.
 */
export function ConfirmForm({
  pending,
  failure,
  explanationId,
  onDelete,
  onEdit,
}: ConfirmFormProps) {
  const [typed, setTyped] = useState("");
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
          setTyped(value);
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
