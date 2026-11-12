import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import type { QuizSummaryView } from "../viewTypes";
import { QuizAction } from "./QuizAction";
import { StateLine } from "./StateLine";

interface QuizItemProps {
  item: QuizSummaryView;
  pending: boolean;
  onPrepare: (moduleId: string) => void;
  onOpen: (quizId: string) => void;
}

/** Une ligne de la liste : module, semaine, meilleur score, prochain essai et action. */
export function QuizItem(props: QuizItemProps) {
  const { item } = props;
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 rounded-xl border bg-card p-4">
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">
          {t("quiz.list.week", { rank: item.weekRank })}
        </p>
        <h3 className="font-medium">{item.moduleTitle}</h3>
        <p className="text-sm text-muted-foreground">
          <StateLine item={item} />
          {item.retryOn !== null ? (
            <>
              {" · "}
              <span>{t("quiz.list.retryOn", { date: longDay(item.retryOn) })}</span>
            </>
          ) : null}
        </p>
      </div>
      <QuizAction {...props} />
    </li>
  );
}
