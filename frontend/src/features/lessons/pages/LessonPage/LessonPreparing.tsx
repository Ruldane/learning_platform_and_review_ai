import { Loader2, TriangleAlert } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { LessonOut } from "../../types";

/**
 * Une leçon qui n'est pas lisible : pas encore lancée, en cours d'écriture (elle peut y rester
 * longtemps : la page se relit toute seule) ou en échec avec sa raison et la nouvelle tentative.
 */
export function LessonPreparing({ lesson }: { lesson: LessonOut }) {
  if (lesson.status === "failed") {
    return (
      <section
        role="alert"
        aria-labelledby="lesson-state-title"
        className="flex items-start gap-3 rounded-xl border border-destructive/40 bg-card p-5"
      >
        <TriangleAlert aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-destructive" />
        <div className="flex flex-col gap-1">
          <h2 id="lesson-state-title" className="font-semibold">
            {t("lessons.preparing.failedTitle")}
          </h2>
          <p>{lesson.failure_reason ?? t("lessons.preparing.failedNoReason")}</p>
          <p className="text-sm text-muted-foreground">{t("lessons.preparing.failedNext")}</p>
        </div>
      </section>
    );
  }
  const generating = lesson.status === "generating";
  return (
    <section
      role="status"
      aria-labelledby="lesson-state-title"
      className="flex items-start gap-3 rounded-xl border bg-card p-5"
    >
      <Loader2
        aria-hidden="true"
        className={`mt-0.5 size-5 shrink-0 ${generating ? "animate-spin motion-reduce:animate-none" : ""}`}
      />
      <div className="flex flex-col gap-1">
        <h2 id="lesson-state-title" className="font-semibold">
          {t("lessons.preparing.title")}
        </h2>
        <p className="text-muted-foreground">
          {generating
            ? t("lessons.preparing.generating")
            : t("lessons.preparing.pending", { rank: lesson.week_rank })}
        </p>
      </div>
    </section>
  );
}
