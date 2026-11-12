import type { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";

const STATUSES = ["running", "waiting_user", "paused", "completed", "failed", "cancelled"] as const;
type Status = (typeof STATUSES)[number];

/** Statut de session lu dans les détails d'un 409 `program_not_waiting`. */
function statusIn(details: unknown): Status | null {
  const status = (details as { status?: unknown } | null)?.status;
  return STATUSES.find((known) => known === status) ?? null;
}

/**
 * Les conflits qui ne sont pas des erreurs : le programme n'attend plus cette réponse (`program_not_waiting`,
 * `stale_interrupt`). Le texte dit pourquoi ; l'appelant relit l'état. `null` : une vraie erreur.
 */
export function conflictNotice(failure: ApiError): string | null {
  if (failure.code === "stale_interrupt") return t("program.validation.stale");
  if (failure.code !== "program_not_waiting") return null;
  const status = statusIn(failure.details);
  return status === null
    ? t("program.validation.notWaitingUnknown")
    : t("program.validation.notWaiting", { status: t(`session.status.${status}`) });
}
