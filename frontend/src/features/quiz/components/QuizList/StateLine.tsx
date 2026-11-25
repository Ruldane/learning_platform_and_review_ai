import { t } from "@/shared/i18n/t";
import type { QuizSummaryView } from "../viewTypes";

/** Where the module stands: best score, preparation running or failed, or not yet tried. */
export function StateLine({ item }: { item: QuizSummaryView }) {
  if (item.bestScore !== null) {
    return <span>{t("quiz.list.bestScore", { score: item.bestScore })}</span>;
  }
  if (item.status === "generating") return <span>{t("quiz.list.preparing")}</span>;
  if (item.status === "failed") return <span>{t("quiz.list.failed")}</span>;
  return <span>{t("quiz.list.noScore")}</span>;
}
