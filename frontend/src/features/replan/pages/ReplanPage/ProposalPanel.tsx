import { t } from "@/shared/i18n/t";
import { PlanDiff } from "@/shared/session-ui";
import { WeekLoadTable } from "../../components/WeekLoadTable";
import type { VersionView } from "../../components/viewTypes";
import { ProposalBlock } from "./ProposalBlock";

/**
 * La proposition qui attend une réponse : le bilan de la semaine, les changements (ajoutées,
 * retirées, déplacées, et la durée du programme quand l'échéance bouge) et la charge de chaque
 * semaine avant et après, sous son plafond. La réponse se donne dans la carte du fil.
 */
export function ProposalPanel({ version }: { version: VersionView }) {
  return (
    <section
      aria-label={t("replan.proposal.heading")}
      className="flex flex-col gap-4 rounded-xl border-2 border-primary bg-card p-4"
    >
      <h2 className="text-lg font-semibold">
        {t("replan.proposal.heading")} ({t("replan.history.version", { version: version.version })})
      </h2>
      {version.review ? (
        <ProposalBlock title={t("replan.proposal.review")}>
          <p className="whitespace-pre-line text-sm">{version.review}</p>
        </ProposalBlock>
      ) : null}
      {version.diff ? (
        <ProposalBlock title={t("replan.proposal.changes")}>
          {version.weeks && version.weeks.before !== version.weeks.after ? (
            <p className="text-sm font-medium">
              {t("replan.proposal.weeks", {
                before: version.weeks.before,
                after: version.weeks.after,
              })}
            </p>
          ) : null}
          <PlanDiff diff={version.diff} />
        </ProposalBlock>
      ) : null}
      <ProposalBlock title={t("replan.proposal.loads")}>
        <WeekLoadTable loads={version.weekLoads} />
      </ProposalBlock>
    </section>
  );
}
