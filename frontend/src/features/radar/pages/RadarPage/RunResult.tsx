import { t } from "@/shared/i18n/t";
import { fullDateTime } from "@/shared/lib/relativeTime";
import { RadarAlerts } from "../../components/RadarAlerts";
import { RadarOffers } from "../../components/RadarOffers";
import { RadarSummary } from "../../components/RadarSummary";
import { SkillRanking } from "../../components/SkillRanking";
import type { RunView } from "../../toView";

/** Le résultat d'un relevé fini : ce qui a été lu, le classement, les alertes et les offres. */
export function RunResult({ run }: { run: RunView }) {
  return (
    <div className="flex flex-col gap-4">
      <h2 className="text-xl font-semibold">
        {t("radar.page.runOf", { when: fullDateTime(run.finishedAt ?? run.createdAt) })}
      </h2>
      <RadarSummary run={run.summary} />
      <section aria-labelledby="radar-ranking" className="flex flex-col gap-2">
        <h2 id="radar-ranking" className="text-lg font-medium">
          {t("radar.ranking.title")}
        </h2>
        <SkillRanking ranking={run.ranking} />
      </section>
      <RadarAlerts alerts={run.alerts} />
      <RadarOffers offers={run.offers} />
    </div>
  );
}
