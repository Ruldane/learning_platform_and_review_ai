import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { ConfirmForm, type DeleteFailure } from "./ConfirmForm";
import { DeleteExplanation } from "./DeleteExplanation";

interface DeleteAccountCardProps {
  pending: boolean;
  /** Un nouvel objet à chaque échec : le focus passe au message même pour un échec répété. */
  failure: DeleteFailure | null;
  onDelete: (confirm: string) => void;
}

/** « Tout supprimer » : ce qui part et ce qui reste, puis le mot à retaper pour confirmer. */
export function DeleteAccountCard({ pending, failure, onDelete }: DeleteAccountCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-3 rounded-xl border border-destructive/40 bg-card p-4"
    >
      <h2 id={titleId} className="text-lg font-semibold">
        {t("account.delete.title")}
      </h2>
      <DeleteExplanation />
      <ConfirmForm pending={pending} failure={failure} onDelete={onDelete} />
    </section>
  );
}
