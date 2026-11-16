import { t } from "@/shared/i18n/t";
import { EvaluationView } from "../../components/EvaluationView";
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
}

/**
 * Ce que le statut du projet demande ensuite : rendre (`todo`), reprendre à la lumière de
 * l'évaluation (`to_redo`), attendre et suivre l'évaluation (`reviewing`), ou la suite d'un projet
 * validé. Un énoncé en préparation ou en échec n'a rien de plus à montrer ici.
 */
export function StatusSections({ project, run, submitter }: StatusSectionsProps) {
  const criteria = project.brief?.criteria ?? [];
  switch (project.status) {
    case "todo":
      return <SubmitSection submitter={submitter} />;
    case "to_redo":
      return (
        <>
          {project.evaluation ? (
            <EvaluationView evaluation={project.evaluation} criteria={criteria} />
          ) : null}
          <p className="text-sm font-medium">{t("projects.page.toRedo")}</p>
          <SubmitSection submitter={submitter} />
        </>
      );
    case "reviewing":
      return (
        <RunPanel
          title={t("projects.page.reviewing")}
          text={t("projects.page.reviewingText")}
          note={submitter.resumed ? t("projects.page.resumed") : null}
          run={run}
          sessionId={project.sessionId}
        />
      );
    case "validated":
      return <ValidatedSections project={project} criteria={criteria} />;
    default:
      return null;
  }
}
