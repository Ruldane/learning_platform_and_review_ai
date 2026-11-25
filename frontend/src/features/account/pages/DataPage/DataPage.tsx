import { useQuery } from "@tanstack/react-query";
import { useMemo } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { AccountChangedError, exportUrl, fetchMe } from "../../api";
import { DeleteAccountCard, type DeleteFailure } from "../../components/DeleteAccountCard";
import { ExportCard } from "../../components/ExportCard";
import { useDeleteAccount } from "../../hooks/useDeleteAccount";
import { accountKeys } from "../../queryKeys";

const CONFIRMATION_REQUIRED = "confirmation_required";
/** The first vector erasure happens before the rows are deleted (P19). */
const VECTOR_UNAVAILABLE = "vector_store_unavailable";

/** A refusal that targets the confirmation field: its code, or a 422 naming `confirm`. */
function refusesConfirmation(error: ApiError): boolean {
  if (error.code === CONFIRMATION_REQUIRED) return true;
  const details = error.details;
  if (error.status !== 422 || typeof details !== "object" || details === null) return false;
  const fields = (details as { fields?: unknown }).fields;
  return Array.isArray(fields) && fields.includes("confirm");
}

/**
 * The text of a deletion failure. A confirmation refusal has its own text (never the
 * input, even if the server sends it back); any other error keeps the backend message, then says
 * what
 * is certain about the state of the deletion.
 */
function describeFailure(error: unknown, sent: boolean): DeleteFailure {
  if (error instanceof AccountChangedError) {
    return { message: t("account.delete.accountChanged"), field: false };
  }
  if (error instanceof ApiError && refusesConfirmation(error)) {
    return { message: t("account.delete.confirmationRequired"), field: true };
  }
  if (error instanceof ApiError && error.code === VECTOR_UNAVAILABLE) {
    return { message: t("account.delete.rowsUntouched"), field: false };
  }
  const hint = t(sent ? "account.delete.retry" : "account.delete.notStarted");
  return { message: `${errorMessage(error)} ${hint}`, field: false };
}

/** Réglages > Mes données (SPEC 17.3): export all your data, or delete everything. */
export function DataPage() {
  const { data: me } = useQuery({
    queryKey: accountKeys.me,
    queryFn: ({ signal }) => fetchMe(signal),
    enabled: false, // observes the identity loaded by the login gate
  });
  const remove = useDeleteAccount(me);
  const { error, started } = remove;
  // `started` reads a ref set before the error: the failure object stays new on each error.
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
      {me && (
        <DeleteAccountCard
          accountLabel={me.email ?? t("account.delete.localIdentity")}
          consentScope={`${me.id}:${me.auth_mode}:${remove.consentRevision}`}
          pending={remove.isPending}
          failure={failure}
          onDelete={remove.submit}
          onEdit={remove.reset}
        />
      )}
    </div>
  );
}
