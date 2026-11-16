import { t } from "@/shared/i18n/t";
import type { RunSummaryView } from "../viewTypes";
import { BlockedDomains } from "./BlockedDomains";

interface RadarSummaryProps {
  run: RunSummaryView;
}

function plural(count: number, key: "read" | "blocked" | "analyzed"): string {
  const base = `radar.summary.${key}` as const;
  return count === 1 ? t(`${base}.one`) : t(`${base}.many`, { count });
}

/**
 * Ce que le relevé a réellement lu : « 47 offres lues · 6 bloquées · 41 analysées », les domaines
 * bloqués à part (dépliables), et le bandeau d'échantillon réduit quand il y a moins de 30 offres.
 */
export function RadarSummary({ run }: RadarSummaryProps) {
  return (
    <section
      aria-labelledby="radar-summary"
      className="flex flex-col gap-2 rounded-xl border bg-card p-4"
    >
      <h2 id="radar-summary" className="text-lg font-medium">
        {t("radar.summary.title")}
      </h2>
      <p className="text-sm text-muted-foreground">
        {t("radar.summary.scope", { role: run.role, zone: run.zone })}
      </p>
      <p className="font-medium tabular-nums">
        {[
          plural(run.readCount, "read"),
          plural(run.blockedCount, "blocked"),
          plural(run.analyzed, "analyzed"),
        ].join(" · ")}
      </p>
      {run.notPostings > 0 ? (
        <p className="text-sm text-muted-foreground">
          {run.notPostings === 1
            ? t("radar.summary.notPostings.one")
            : t("radar.summary.notPostings.many", { count: run.notPostings })}
        </p>
      ) : null}
      <BlockedDomains domains={run.blockedDomains} />
      {run.lowSample ? (
        <p
          role="note"
          className="rounded-lg border border-amber-500/60 bg-amber-500/10 p-3 text-sm"
        >
          {t("radar.summary.lowSample")}
        </p>
      ) : null}
    </section>
  );
}
