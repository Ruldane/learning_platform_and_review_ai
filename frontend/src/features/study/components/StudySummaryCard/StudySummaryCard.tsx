import { useId } from "react";
import { t } from "@/shared/i18n/t";
import { formatMinutes } from "@/shared/lib/format";
import type { StudySummaryView } from "../viewTypes";
import { SummarySection } from "./SummarySection";

interface StudySummaryCardProps {
  summary: StudySummaryView;
}

function cardsText(count: number): string {
  if (count <= 0) return t("study.summary.noCards");
  return t(count === 1 ? "study.summary.cardsOne" : "study.summary.cardsMany", { count });
}

/** Bilan d'une session terminée : résumé, temps travaillé, tâches cochées, fiches créées, acquis. */
export function StudySummaryCard({ summary }: StudySummaryCardProps) {
  const titleId = useId();
  return (
    <section
      aria-labelledby={titleId}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4"
    >
      <header>
        <h2 id={titleId} className="text-lg font-semibold">
          {t("study.summary.title")}
        </h2>
        <p className="text-sm text-muted-foreground">
          {t("study.summary.context", { module: summary.moduleTitle, lesson: summary.lessonTitle })}
        </p>
      </header>
      <p className="whitespace-pre-wrap">{summary.summary}</p>
      <p className="flex flex-wrap items-baseline gap-2 text-sm">
        <span className="text-muted-foreground">{t("study.summary.minutes")}</span>
        <span className="font-medium tabular-nums">{formatMinutes(summary.minutes)}</span>
      </p>
      <SummarySection
        title={t("study.summary.tasks")}
        empty={t("study.summary.noTasks")}
        items={summary.tasksDone.map((title) => ({ key: title, content: title }))}
      />
      <div>
        <h3 className="text-sm font-medium">{t("study.summary.cards")}</h3>
        <p className="mt-1 text-sm">{cardsText(summary.flashcardsCreated)}</p>
      </div>
      <SummarySection
        title={t("study.summary.skills")}
        empty={t("study.summary.noSkills")}
        items={summary.skills.map((skill) => ({
          key: skill.name,
          content: (
            <span className="flex items-baseline gap-2">
              <span>{skill.name}</span>
              <span className="rounded bg-muted px-1.5 py-0.5 text-xs">
                {t(`study.summary.level.${skill.level}`)}
              </span>
            </span>
          ),
        }))}
      />
    </section>
  );
}
