import { t } from "@/shared/i18n/t";
import type { ProjectionChoices, ProjectionView } from "./components/viewTypes";
import type { Projection, ProjectionQuery } from "./types";

export function toProjectionQuery(choices: ProjectionChoices): ProjectionQuery {
  return {
    role: choices.role,
    zone: choices.zone,
    alternative_weekly_minutes:
      choices.hours === undefined ? undefined : Math.round(choices.hours * 60),
    target_percent: choices.target,
  };
}

export function toProjectionView(projection: Projection): ProjectionView {
  return {
    currentPercent: projection.current_percent,
    offerCount: projection.offer_count,
    sampleId: projection.sample?.run_id ?? null,
    programId: projection.program_id,
    targetPercent: projection.target_percent,
    notes: projection.uncertainty.map((reason) => t(`futureSelf.uncertainty.${reason}`)),
    scenarios: projection.scenarios.map((scenario) => ({
      id: scenario.kind,
      title: t(`futureSelf.kind.${scenario.kind}`),
      weeklyMinutes: scenario.weekly_minutes,
      targetDate: scenario.target_date,
      projectedPercent: scenario.projected_percent,
    })),
    chapters: projection.recommendations.map(({ chapter, offers_unlocked, offers_improved }) => ({
      id: chapter.module_id,
      title: chapter.title,
      link: chapter.lesson_id
        ? `/learn/lessons/${chapter.lesson_id}`
        : `/learn/programs/${chapter.program_id}`,
      minutes: chapter.minutes,
      unlocked: offers_unlocked,
      improved: offers_improved,
    })),
  };
}
