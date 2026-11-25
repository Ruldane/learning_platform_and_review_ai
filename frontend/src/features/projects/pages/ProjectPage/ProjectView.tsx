import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import type { SocketFactory } from "@/shared/realtime/socket";
import { ProjectBriefView } from "../../components/ProjectBriefView";
import { useProjectRun } from "../../hooks/useProjectRun";
import { useRegenerateDrafts } from "../../hooks/useRegenerateDrafts";
import { useSubmitProject } from "../../hooks/useSubmitProject";
import type { ProjectDetailView } from "../../toView";
import { BackLink } from "./BackLink";
import { BriefFailed } from "./BriefFailed";
import { ProjectGithubProofs } from "./ProjectGithubProofs";
import { RunPanel } from "./RunPanel";
import { StatusSections } from "./StatusSections";
import { SubmissionHistory } from "./SubmissionHistory";

interface ProjectViewProps {
  project: ProjectDetailView;
  createSocket?: SocketFactory;
}

/** Statuses where a session runs for the project: brief being written or submission evaluated. */
const FOLLOWED = ["brief_pending", "reviewing"];

/**
 * A project as read: its title and written status, the brief (or its stand-in), what its
 * status asks next (submit, follow the evaluation, or the next step for a validated project), then
 * the submission history.
 */
export function ProjectView({ project, createSocket }: ProjectViewProps) {
  const regeneration = useRegenerateDrafts(project.id);
  // A brief or evaluation in progress is followed through the project's session; a validated
  // the session of the drafts it has just retried.
  const sessionId = FOLLOWED.includes(project.status)
    ? project.sessionId
    : project.status === "validated"
      ? regeneration.sessionId
      : null;
  const run = useProjectRun(project.id, sessionId, createSocket);
  const submitter = useSubmitProject(project.id);
  const [retried, setRetried] = useState(false);
  // The focus that « Réessayer l'énoncé » asks for is used once: when the write ends (success or
  // not), it is returned, and a brief retried elsewhere later does not take focus.
  const writing = useRef(false);
  useEffect(() => {
    const pending = project.status === "brief_pending";
    if (writing.current && !pending) setRetried(false);
    writing.current = pending;
  }, [project.status]);
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
      <StatusSections
        project={project}
        run={run}
        submitter={submitter}
        regeneration={regeneration}
      />
      {project.submissions.length > 0 && <ProjectGithubProofs projectId={project.id} />}
      <SubmissionHistory submissions={project.submissions} />
    </div>
  );
}
