import { t } from "@/shared/i18n/t";
import { clockTime } from "@/shared/lib/relativeTime";
import type { RelayStatus } from "../../api";

export function RelayConnection({ status, failed }: { status?: RelayStatus; failed: boolean }) {
  const state = status?.state ?? (failed ? "unknown" : "checking");
  return (
    <aside className="grid gap-2 rounded-xl border bg-card p-4" aria-label={t("brain.connection.title")}>
      <p role="status" className="font-medium">{t(`brain.connection.${state}`)}</p>
      {status?.last_contact ? <p className="text-sm text-muted-foreground">
        {t("brain.connection.lastContact", { time: clockTime(status.last_contact) })}
      </p> : null}
      {state === "waiting" || state === "offline" || state === "unconfigured" ? (
        <p className="text-sm">{t("brain.connection.instructions", { variable: "TREMPLIN_BRAIN_SYNC_TOKEN" })}</p>
      ) : null}
    </aside>
  );
}
