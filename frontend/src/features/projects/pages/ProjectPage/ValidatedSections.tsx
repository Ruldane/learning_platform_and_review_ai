import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import { EvaluationView } from "../../components/EvaluationView";
import { formatDay } from "../../format";
import type { DraftsRegeneration } from "../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../hooks/useProjectRun";
import { SKILLS_MAP_PATH } from "../../paths";
import type { ProjectDetailView } from "../../toView";
import { DraftsSection } from "./DraftsSection";
import { EntrySection } from "./EntrySection";

/**
 * A validated project: the finding (and the link to the skills map, where the module's skills
 * are proven), the evaluation, the drafts in January's name, then the profile addition
 * (without drafts, they are regenerated).
 */
export function ValidatedSections({
  project,
  criteria,
  regeneration,
  run,
}: {
  project: ProjectDetailView;
  criteria: string[];
  regeneration: DraftsRegeneration;
  run: ReturnType<typeof useProjectRun>;
}) {
  return (
    <>
      <section
        aria-labelledby="project-validated"
        className="flex flex-col gap-2 rounded-xl border bg-card p-4 text-sm"
      >
        <h2 id="project-validated" className="text-lg font-medium">
          {t("projects.page.validatedTitle")}
        </h2>
        {project.validatedAt ? (
          <p>{t("projects.page.validatedOn", { date: formatDay(project.validatedAt) })}</p>
        ) : null}
        <p>
          {t("projects.page.skillsMapText")}{" "}
          <Link to={SKILLS_MAP_PATH} className="text-primary underline underline-offset-4">
            {t("projects.page.skillsMap")}
          </Link>
        </p>
      </section>
      {project.evaluation ? (
        <EvaluationView evaluation={project.evaluation} criteria={criteria} />
      ) : null}
      <DraftsSection
        projectId={project.id}
        drafts={project.drafts}
        regenerable={project.drafts.length === 0 && project.entryDraft === null}
        regeneration={regeneration}
        run={run}
      />
      <EntrySection project={project} />
    </>
  );
}
