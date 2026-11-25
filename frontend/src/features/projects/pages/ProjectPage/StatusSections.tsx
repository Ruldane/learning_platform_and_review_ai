import { t } from "@/shared/i18n/t";
import { EvaluationView } from "../../components/EvaluationView";
import type { DraftsRegeneration } from "../../hooks/useRegenerateDrafts";
import type { useProjectRun } from "../../hooks/useProjectRun";
import type { useSubmitProject } from "../../hooks/useSubmitProject";
import type { ProjectDetailView } from "../../toView";
import { RunPanel } from "./RunPanel";
import { SubmitSection } from "./SubmitSection";
import { ValidatedSections } from "./ValidatedSections";

interface StatusSectionsProps {
  project: ProjectDetailView;
  run: ReturnType<typeof useProjectRun>;
  submitter: ReturnType<typeof useSubmitProject>;
  regeneration: DraftsRegeneration;
}

/**
 * What the project's status asks next: submit (`todo`), resume in light of the
 * evaluation (`to_redo`), wait and follow the evaluation (`reviewing`), or the next step of a
 * validated project. A brief in preparation or failed has nothing more to show here.
 */
export function StatusSections({ project, run, submitter, regeneration }: StatusSectionsProps) {
  const criteria = project.brief?.criteria ?? [];
  switch (project.status) {
    case "todo":
      return <SubmitSection projectId={project.id} submitter={submitter} />;
    case "to_redo":
      return (
        <>
          {project.evaluation ? (
            <EvaluationView evaluation={project.evaluation} criteria={criteria} />
          ) : null}
          <p className="text-sm font-medium">{t("projects.page.toRedo")}</p>
          <SubmitSection
            projectId={project.id}
            submitter={submitter}
            previous={project.submissions[0] ?? null}
          />
        </>
      );
    case "reviewing":
      return (
        <RunPanel
          title={t("projects.page.reviewing")}
          text={t("projects.page.reviewingText")}
          note={submitter.resumed ? t("projects.page.resumed") : null}
          focusOnMount={submitter.submitted}
          run={run}
          sessionId={project.sessionId}
        />
      );
    case "validated":
      return (
        <ValidatedSections
          project={project}
          criteria={criteria}
          regeneration={regeneration}
          run={run}
        />
      );
    default:
      return null;
  }
}
