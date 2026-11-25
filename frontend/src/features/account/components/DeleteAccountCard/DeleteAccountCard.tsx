import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { ConfirmForm, type DeleteFailure } from "./ConfirmForm";
import { DeleteExplanation } from "./DeleteExplanation";

interface DeleteAccountCardProps {
  accountLabel?: string;
  consentScope?: string;
  pending: boolean;
  /** A new object on each failure: focus moves to the message, even for a repeated failure. */
  failure: DeleteFailure | null;
  onDelete: (confirm: string) => void;
  /** The input changed: a failure already shown no longer applies. */
  onEdit: () => void;
}

/** « Tout supprimer »: what is removed and what stays, then the word to retype to confirm. */
export function DeleteAccountCard({
  accountLabel,
  consentScope = "",
  pending,
  failure,
  onDelete,
  onEdit,
}: DeleteAccountCardProps) {
  const titleId = useId();
  const explanationId = useId();
  const accountId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-3 rounded-xl border border-destructive/40 bg-card p-4"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {t("account.delete.title")}
      </h2>
      {accountLabel && (
        <p id={accountId} className="text-sm font-medium">
          {t("account.delete.identity", { account: accountLabel })}
        </p>
      )}
      <DeleteExplanation id={explanationId} />
      <ConfirmForm
        consentScope={consentScope}
        pending={pending}
        failure={failure}
        explanationId={accountLabel ? `${accountId} ${explanationId}` : explanationId}
        onDelete={onDelete}
        onEdit={onEdit}
      />
    </section>
  );
}
