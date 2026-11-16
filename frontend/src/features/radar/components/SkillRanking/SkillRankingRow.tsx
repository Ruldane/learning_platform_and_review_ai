import { t } from "@/shared/i18n/t";
import type { SkillTrendView } from "../viewTypes";

/** L'évolution en toutes lettres : jamais la couleur seule (« +8 pts », « −2 pts », « nouvelle »). */
function evolutionText(item: SkillTrendView): string {
  if (item.isNew) return t("radar.ranking.new");
  if (item.deltaShare === null) return t("radar.ranking.first");
  if (item.deltaShare > 0) return t("radar.ranking.gain", { points: item.deltaShare });
  if (item.deltaShare < 0) return t("radar.ranking.loss", { points: Math.abs(item.deltaShare) });
  return t("radar.ranking.same");
}

function evolutionTone(item: SkillTrendView): string {
  if (item.isNew || (item.deltaShare ?? 0) > 0) return "text-emerald-700 dark:text-emerald-400";
  if ((item.deltaShare ?? 0) < 0) return "text-destructive";
  return "text-muted-foreground";
}

/** Une ligne du classement : le texte dit tout, la barre ne fait que l'illustrer. */
export function SkillRankingRow({ item }: { item: SkillTrendView }) {
  const percent = Math.round(item.share * 100);
  return (
    <li className="flex flex-col gap-1">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="w-8 text-right font-medium tabular-nums">
          {t("radar.ranking.rank", { rank: item.rank })}
        </span>
        <span className="min-w-0 flex-1 font-medium">{item.skill}</span>
        <span className="tabular-nums">{t("radar.ranking.share", { share: percent })}</span>
        <span className={`text-sm font-medium tabular-nums ${evolutionTone(item)}`}>
          {evolutionText(item)}
        </span>
      </div>
      <div aria-hidden="true" className="h-2 w-full overflow-hidden rounded-full bg-muted">
        <div className="h-full rounded-full bg-primary" style={{ width: `${percent}%` }} />
      </div>
    </li>
  );
}
