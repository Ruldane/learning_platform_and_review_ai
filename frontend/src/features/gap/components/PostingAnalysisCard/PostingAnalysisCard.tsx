import { t } from "@/shared/i18n/t";
import type { PostingAnalysisView } from "../viewTypes";
import { Chips } from "./Chips";
import { Requirements } from "./Requirements";

interface PostingAnalysisCardProps {
  analysis: PostingAnalysisView;
  /** False when the page already shows the posting title (only one title on screen). */
  showTitle?: boolean;
}

const KNOWN_LEVELS = ["junior", "mid_level", "senior", "lead"] as const;

function levelText(level: string): string {
  const known = KNOWN_LEVELS.find((key) => key === level);
  return known ? t(`gap.analysis.level.${known}`) : t("gap.analysis.levelUnknown");
}

/**
 * What the analysis understood of the posting: role, company, level, place, requirements, keywords,
 * knock-out criteria, tools. All of it is plain text: nothing in the posting is interpreted.
 */
export function PostingAnalysisCard({ analysis, showTitle = true }: PostingAnalysisCardProps) {
  const facts = [
    analysis.company ? t("gap.analysis.company", { company: analysis.company }) : null,
    t("gap.analysis.levelLabel", { level: levelText(analysis.level) }),
    analysis.location ? t("gap.analysis.location", { location: analysis.location }) : null,
    analysis.remote ? t("gap.analysis.remote", { remote: analysis.remote }) : null,
  ].filter((fact): fact is string => fact !== null);
  return (
    <section
      aria-label={t("gap.analysis.label")}
      className="flex flex-col gap-3 rounded-xl border bg-card p-4"
    >
      {showTitle ? <h3 className="text-lg font-medium">{analysis.title}</h3> : null}
      <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted-foreground">
        {facts.map((fact) => (
          <li key={fact}>{fact}</li>
        ))}
      </ul>
      <Chips title={t("gap.analysis.eliminatory")} items={analysis.eliminatory} />
      <Requirements items={analysis.requirements} />
      <Chips title={t("gap.analysis.keywords")} items={analysis.keywords} />
      <Chips title={t("gap.analysis.tools")} items={analysis.tools} />
    </section>
  );
}
