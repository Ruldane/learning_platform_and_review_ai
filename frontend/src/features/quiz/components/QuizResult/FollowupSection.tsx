import { TriangleAlert } from "lucide-react";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import type { FollowupView } from "../viewTypes";

/**
 * Ce qui suit un quiz raté : les révisions ajoutées au planning, la date du nouvel essai et, s'il
 * y en a, l'avertissement des révisions que le budget n'a pas pu accueillir.
 */
export function FollowupSection({ followup }: { followup: FollowupView }) {
  const { revisionTasks, retryOn, unplaced } = followup;
  return (
    <section className="flex flex-col gap-2 rounded-xl border bg-card p-4">
      {revisionTasks.length > 0 ? (
        <>
          <p className="text-sm font-medium">{t("quiz.result.followup.tasks")}</p>
          <ul
            aria-label={t("quiz.result.followup.tasks")}
            className="list-inside list-disc text-sm"
          >
            {revisionTasks.map((title, index) => (
              <li key={index}>{title}</li>
            ))}
          </ul>
        </>
      ) : null}
      {retryOn !== null ? (
        <p className="text-sm">{t("quiz.result.followup.retry", { date: longDay(retryOn) })}</p>
      ) : null}
      {unplaced > 0 ? (
        <p
          role="status"
          className="flex items-start gap-2 rounded-lg border border-amber-700/40 bg-amber-50 p-2 text-sm text-amber-900"
        >
          <TriangleAlert aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
          {t(
            unplaced === 1
              ? "quiz.result.followup.unplacedOne"
              : "quiz.result.followup.unplacedMany",
            { count: unplaced },
          )}
        </p>
      ) : null}
    </section>
  );
}
