import { useMemo } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { exportUrl } from "../../api";
import { DeleteAccountCard, type DeleteFailure } from "../../components/DeleteAccountCard";
import { ExportCard } from "../../components/ExportCard";
import { useDeleteAccount } from "../../hooks/useDeleteAccount";

const CONFIRMATION_REQUIRED = "confirmation_required";
/** Le 503 de la mémoire vectorielle tombe avant toute suppression (P19). */
const VECTOR_UNAVAILABLE = "vector_store_unavailable";

/** Un refus qui vise le champ de confirmation : son code, ou un 422 qui nomme `confirm`. */
function refusesConfirmation(error: ApiError): boolean {
  if (error.code === CONFIRMATION_REQUIRED) return true;
  const details = error.details;
  if (error.status !== 422 || typeof details !== "object" || details === null) return false;
  const fields = (details as { fields?: unknown }).fields;
  return Array.isArray(fields) && fields.includes("confirm");
}

/**
 * Le texte d'un échec de suppression. Un refus de la confirmation a son propre texte (jamais la
 * saisie, même renvoyée par le serveur) ; toute autre erreur garde le message du back, puis dit ce
 * qui est sûr : « rien n'a été supprimé » quand la suppression n'est pas partie (mode illisible)
 * ou s'est arrêtée avant d'effacer quoi que ce soit, sinon qu'elle reprend là où elle s'est arrêtée.
 */
function describeFailure(error: unknown, sent: boolean): DeleteFailure {
  if (error instanceof ApiError && refusesConfirmation(error)) {
    return { message: t("account.delete.confirmationRequired"), field: true };
  }
  const untouched = !sent || (error instanceof ApiError && error.code === VECTOR_UNAVAILABLE);
  const hint = t(untouched ? "account.delete.notStarted" : "account.delete.retry");
  return { message: `${errorMessage(error)} ${hint}`, field: false };
}

/** Réglages > Mes données (SPEC 17.3) : exporter toutes ses données, ou tout supprimer. */
export function DataPage() {
  const remove = useDeleteAccount();
  const { error, started } = remove;
  // `started` lit une ref posée avant l'erreur : l'objet d'échec reste neuf à chaque erreur.
  const failure = useMemo(
    () => (error ? describeFailure(error, started()) : null),
    [error, started],
  );
  return (
    <div className="flex flex-col gap-6">
      <header>
        <h1 className="text-2xl font-semibold">{t("account.title")}</h1>
        <p className="mt-1 text-muted-foreground">{t("account.intro")}</p>
      </header>
      <ExportCard href={exportUrl} />
      <DeleteAccountCard
        pending={remove.isPending}
        failure={failure}
        onDelete={remove.submit}
        onEdit={remove.reset}
      />
    </div>
  );
}
