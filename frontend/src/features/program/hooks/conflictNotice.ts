import type { ApiError } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";

const STATUSES = ["running", "waiting_user", "paused", "completed", "failed", "cancelled", "expired"] as const;
type Status = (typeof STATUSES)[number];

/** Session status read from the details of a 409 `program_not_waiting`. */
function statusIn(details: unknown): Status | null {
  const status = (details as { status?: unknown } | null)?.status;
  return STATUSES.find((known) => known === status) ?? null;
}

/**
 * Conflicts, not errors: the program no longer waits for this (`program_not_waiting`,
 * `stale_interrupt`). The text says why; the caller re-reads the state. `null`: a real error.
 */
export function conflictNotice(failure: ApiError): string | null {
  if (failure.code === "stale_interrupt") return t("program.validation.stale");
  if (failure.code !== "program_not_waiting") return null;
  const status = statusIn(failure.details);
  return status === null
    ? t("program.validation.notWaitingUnknown")
    : t("program.validation.notWaiting", { status: t(`session.status.${status}`) });
}
