import { t } from "@/shared/i18n/t";
import type { BriefDataView } from "../viewTypes";
import { BriefList } from "./BriefList";

interface ProjectBriefViewProps {
  brief: BriefDataView;
}

/** A project's brief: goal, context, constraints, criteria, expected deliverable and duration. */
export function ProjectBriefView({ brief }: ProjectBriefViewProps) {
  return (
    <article className="flex flex-col gap-4 rounded-xl border bg-card p-4 text-sm">
      <h2 className="text-lg font-medium">{brief.title}</h2>
      <section className="flex flex-col gap-1">
        <h3 className="font-medium">{t("projects.brief.objective")}</h3>
        <p>{brief.objective}</p>
      </section>
      <section className="flex flex-col gap-1">
        <h3 className="font-medium">{t("projects.brief.context")}</h3>
        <p>{brief.context}</p>
      </section>
      <BriefList title={t("projects.brief.constraints")} items={brief.constraints} />
      <BriefList title={t("projects.brief.criteria")} items={brief.criteria} ordered />
      <section className="flex flex-col gap-1">
        <h3 className="font-medium">{t("projects.brief.deliverable")}</h3>
        <p>{t(`projects.brief.deliverables.${brief.deliverable}`)}</p>
      </section>
      <p className="text-muted-foreground tabular-nums">
        {t("projects.brief.hours", { hours: brief.hours })}
      </p>
    </article>
  );
}
