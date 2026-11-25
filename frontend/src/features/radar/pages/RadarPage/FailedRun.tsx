import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { failureReason } from "../../errors";
import type { RunView } from "../../toView";

/** A failed sweep: it says why in plain words (the server code, never a raw message). */
export function FailedRun({ run }: { run: RunView }) {
  return (
    <section
      aria-labelledby="radar-failed"
      className="flex flex-col gap-2 rounded-xl border border-destructive/40 bg-card p-4"
    >
      <h2 id="radar-failed" className="text-lg font-medium">
        {t("radar.failure.title")}
      </h2>
      <p className="text-sm text-muted-foreground">
        {t("radar.page.runOf", { when: fullDateTime(run.createdAt) })}
        {" · "}
        {t("radar.summary.scope", { role: run.summary.role, zone: run.summary.zone })}
      </p>
      <p>{t("radar.failure.reason", { reason: failureReason(run.errorCode) })}</p>
      <p className="text-sm text-muted-foreground">{t("radar.failure.retry")}</p>
    </section>
  );
}
