import { useMemo } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { exportUrl } from "../../api";
import { DeleteAccountCard, type DeleteFailure } from "../../components/DeleteAccountCard";
import { ExportCard } from "../../components/ExportCard";
import { useDeleteAccount } from "../../hooks/useDeleteAccount";

const CONFIRMATION_REQUIRED = "confirmation_required";

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
 * saisie, même renvoyée par le serveur) ; toute autre erreur garde le message du back, avec la
 * promesse que rejouer l'appel reprend où il s'est arrêté.
 */
function describeFailure(error: unknown): DeleteFailure {
  if (error instanceof ApiError && refusesConfirmation(error)) {
    return { message: t("account.delete.confirmationRequired"), field: true };
  }
  return { message: `${errorMessage(error)} ${t("account.delete.retry")}`, field: false };
}

/** Réglages > Mes données (SPEC 17.3) : exporter toutes ses données, ou tout supprimer. */
export function DataPage() {
  const remove = useDeleteAccount();
  const failure = useMemo(
    () => (remove.error ? describeFailure(remove.error) : null),
    [remove.error],
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
        onDelete={(confirm) => remove.mutate(confirm)}
      />
    </div>
  );
}
