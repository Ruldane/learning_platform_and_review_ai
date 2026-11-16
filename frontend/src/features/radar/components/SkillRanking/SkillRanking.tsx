import { t } from "@/shared/i18n/t";
import type { SkillTrendView } from "../viewTypes";
import { SkillRankingRow } from "./SkillRankingRow";

interface SkillRankingProps {
  ranking: SkillTrendView[];
}

/** Le classement des compétences demandées : rang, nom, part en texte et en barre, évolution écrite. */
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
