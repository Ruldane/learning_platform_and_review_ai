import { useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ProjectBriefView } from "../../components/ProjectBriefView";
import { useProjectRun } from "../../hooks/useProjectRun";
import { useSubmitProject } from "../../hooks/useSubmitProject";
import type { ProjectDetailView } from "../../toView";
import { BackLink } from "./BackLink";
import { BriefFailed } from "./BriefFailed";
import { RunPanel } from "./RunPanel";
import { StatusSections } from "./StatusSections";
import { SubmissionHistory } from "./SubmissionHistory";

interface ProjectViewProps {
  project: ProjectDetailView;
  createSocket?: SocketFactory;
}

/** Les statuts où une session tourne pour le projet : l'énoncé s'écrit, ou le rendu s'évalue. */
const FOLLOWED = ["brief_pending", "reviewing"];

/**
 * Un projet lu : son titre et son statut écrit, l'énoncé (ou ce qui en tient lieu), ce que son
 * statut demande ensuite (rendre, suivre l'évaluation, ou la suite d'un projet validé), puis
 * l'historique des rendus.
 */
export function ProjectView({ project, createSocket }: ProjectViewProps) {
  const sessionId = FOLLOWED.includes(project.status) ? project.sessionId : null;
  const run = useProjectRun(project.id, sessionId, createSocket);
  const submitter = useSubmitProject(project.id);
  const [retried, setRetried] = useState(false);
  return (
    <div className="flex flex-col gap-6">
      <header className="flex flex-col gap-2">
        <BackLink />
        <h1 className="text-2xl font-semibold">{project.title}</h1>
        <p className="font-medium">
          {t("projects.card.statusLabel", { status: t(`projects.card.status.${project.status}`) })}
        </p>
      </header>
      {project.brief ? <ProjectBriefView brief={project.brief} /> : null}
      {project.status === "brief_pending" ? (
        <RunPanel
          title={t("projects.page.briefTitle")}
          text={t("projects.page.briefPending")}
          focusOnMount={retried}
          run={run}
          sessionId={sessionId}
        />
      ) : null}
      {project.status === "brief_failed" ? (
        <BriefFailed projectId={project.id} onRetried={() => setRetried(true)} />
      ) : null}
      <StatusSections project={project} run={run} submitter={submitter} />
      <SubmissionHistory submissions={project.submissions} />
    </div>
  );
}
