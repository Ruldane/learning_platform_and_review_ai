import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import type { DeleteFailure } from "./ConfirmForm";

const ALERT_CLASS =
  "rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive outline-none " +
  "focus-visible:ring-3 focus-visible:ring-ring";

interface FormFeedbackProps {
  pending: boolean;
  failure: DeleteFailure | null;
  /** L'identifiant du message d'échec, cité par le champ. */
  messageId: string;
  /** Le message d'échec reçoit le focus à chaque nouvel échec. */
  messageRef: Ref<HTMLParagraphElement>;
}

/**
 * L'attente (annoncée : la zone `status` est toujours dans la page, seul son texte change) et
 * l'échec de la suppression.
 */
export function FormFeedback({ pending, failure, messageId, messageRef }: FormFeedbackProps) {
  return (
    <>
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">
        {pending ? t("account.delete.waiting") : null}
      </p>
      {failure ? (
        <p id={messageId} ref={messageRef} role="alert" tabIndex={-1} className={ALERT_CLASS}>
          {failure.message}
        </p>
      ) : null}
    </>
  );
}
