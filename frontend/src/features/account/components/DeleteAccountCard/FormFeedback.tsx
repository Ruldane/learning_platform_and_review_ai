import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import type { DeleteFailure } from "./ConfirmForm";

const ALERT_CLASS =
  "rounded-lg border border-destructive/40 px-3 py-2 text-sm text-destructive outline-none " +
  "focus-visible:ring-3 focus-visible:ring-ring";

interface FormFeedbackProps {
  pending: boolean;
  failure: DeleteFailure | null;
  /** The identifier of the failure message, referenced by the field. */
  messageId: string;
  /** The failure message receives focus on each new failure. */
  messageRef: Ref<HTMLParagraphElement>;
}

/**
 * The wait (announced: the `status` region is always on the page, only its text changes) and
 * the deletion failure: a paragraph that takes focus, without `role="alert"` (the screen reader
 * reads it once, on focus, not twice: once by the alert and then by focus).
 */
export function FormFeedback({ pending, failure, messageId, messageRef }: FormFeedbackProps) {
  return (
    <>
      <p role="status" className="text-sm text-muted-foreground empty:sr-only">
        {pending ? t("account.delete.waiting") : null}
      </p>
      {failure ? (
        <p
          id={messageId}
          ref={messageRef}
          data-testid="delete-failure"
          tabIndex={-1}
          className={ALERT_CLASS}
        >
          {failure.message}
        </p>
      ) : null}
    </>
  );
}
