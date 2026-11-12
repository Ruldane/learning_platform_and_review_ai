import { t } from "@/shared/i18n/t";
import { cn } from "@/shared/lib/utils";
import { ProposalActions, type ProposalActionsProps } from "./ProposalActions";
import { ProposalSection } from "./ProposalSection";

const HOURS = new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 1 });

/**
 * Une proposition de parcours. Ses six rubriques (en-tête, durée et charge, compétences, projet
 * final, compromis, actions) occupent six lignes d'une grille commune aux cartes (`subgrid`) : elles
 * s'alignent d'une carte à l'autre, quelle que soit la longueur des textes.
 */
export function ProposalCard(props: ProposalActionsProps) {
  const { proposal } = props;
  const weeks =
    proposal.durationWeeks === 1 ? "learning.proposals.weeksOne" : "learning.proposals.weeks";
  return (
    <article
      aria-label={proposal.name}
      className={cn(
        "row-span-6 grid grid-rows-subgrid gap-y-3 rounded-xl border bg-card px-4 py-3 text-sm",
        proposal.chosen ? "border-2 border-primary" : "border-border",
      )}
    >
      <header className="flex flex-col gap-1">
        <p className="text-xs text-muted-foreground">
          {t("learning.proposals.rank", { rank: proposal.rank })}
        </p>
        <h3 className="text-base font-semibold">{proposal.name}</h3>
        <p>{proposal.promise}</p>
      </header>
      <div className="grid grid-cols-2 gap-2">
        <ProposalSection title={t("learning.proposals.duration")}>
          <p>{t(weeks, { count: proposal.durationWeeks })}</p>
        </ProposalSection>
        <ProposalSection title={t("learning.proposals.workload")}>
          <p>
            {t("learning.proposals.hoursPerWeek", { hours: HOURS.format(proposal.weeklyHours) })}
          </p>
        </ProposalSection>
      </div>
      <ProposalSection title={t("learning.proposals.skills")} items={proposal.skills} />
      <ProposalSection title={t("learning.proposals.finalProject")}>
        <p>{proposal.finalProject}</p>
      </ProposalSection>
      <ProposalSection title={t("learning.proposals.tradeoffs")} items={proposal.tradeoffs} />
      <ProposalActions {...props} />
    </article>
  );
}
