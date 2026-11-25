import { t } from "@/shared/i18n/t";
import type { SkillTrendView } from "../viewTypes";
import { SkillRankingRow } from "./SkillRankingRow";

interface SkillRankingProps {
  ranking: SkillTrendView[];
}

/** The ranking of skills in demand: rank, name, share as text and bar, written trend. */
export function SkillRanking({ ranking }: SkillRankingProps) {
  if (ranking.length === 0) {
    return <p className="text-muted-foreground">{t("radar.ranking.empty")}</p>;
  }
  return (
    <ol aria-label={t("radar.ranking.label")} className="flex flex-col gap-3">
      {ranking.map((item) => (
        <SkillRankingRow key={`${item.rank}-${item.skill}`} item={item} />
      ))}
    </ol>
  );
}
