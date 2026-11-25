import type {
  BriefDataView,
  DraftView,
  EvaluationDataView,
  ProfileEntryView,
  ProjectCardView,
  ProjectStatusView,
} from "./components/viewTypes";
import { projectPath } from "./paths";
import type { ProjectOut, ProjectSummary } from "./types";
import { screenshotUrl } from "./urls";

/** A Portfolio card. */
export function toCardView(project: ProjectSummary): ProjectCardView {
  return {
    id: project.id,
    title: project.title,
    status: project.status,
    hours: project.hours,
    skills: project.skills,
    href: projectPath(project.id),
  };
}

/** The Portfolio groups, in display order: what awaits January first. */
export const GROUP_ORDER: ProjectStatusView[] = [
  "to_redo",
  "todo",
  "reviewing",
  "brief_pending",
  "brief_failed",
  "validated",
];

export interface ProjectGroupView {
  status: ProjectStatusView;
  projects: ProjectCardView[];
}

/** Projects grouped by status; an empty group does not exist, the program order is kept. */
export function groupByStatus(projects: ProjectCardView[]): ProjectGroupView[] {
  return GROUP_ORDER.flatMap((status) => {
    const inGroup = projects.filter((project) => project.status === status);
    return inGroup.length > 0 ? [{ status, projects: inGroup }] : [];
  });
}

/** A screenshot of a submission, with its image address. */
export interface ShotView {
  number: number;
  src: string;
}

/** A submission in the history (latest first). */
export interface SubmissionItemView {
  at: string;
  repoUrl: string | null;
  description: string | null;
  screenshots: ShotView[];
}

/** A project as its page reads it. */
export interface ProjectDetailView {
  id: string;
  title: string;
  status: ProjectStatusView;
  brief: BriefDataView | null;
  evaluation: EvaluationDataView | null;
  submissions: SubmissionItemView[];
  /** The text drafts (CV line, LinkedIn post, README plan), in server order. */
  drafts: (DraftView & { kind: Exclude<DraftView["kind"], "profile_entry"> })[];
  /** The profile-entry draft (its « à vérifier » notice), if it exists. */
  entryDraft: DraftView | null;
  /** The proposed entry for the master profile: the draft, otherwise the project name alone. */
  entry: ProfileEntryView;
  validatedAt: string | null;
  profileVersion: number | null;
  /** The session of the brief or evaluation in progress, otherwise the last one. */
  sessionId: string | null;
}

const toDraft = (draft: ProjectOut["drafts"][number]): DraftView => ({
  kind: draft.kind,
  content: draft.content,
  status: draft.status,
  flags: draft.flags,
  edited: draft.edited,
});

function toEvaluation(project: ProjectOut): EvaluationDataView | null {
  const evaluation = project.evaluation;
  if (!evaluation) return null;
  return {
    verdict: evaluation.verdict,
    feedback: evaluation.feedback,
    repoStatus: evaluation.repo_status,
    results: evaluation.results.map((result) => ({
      index: result.index,
      met: result.met,
      comment: result.comment,
    })),
    // `EvaluationOut` has no such field: the latest submission (the first in the list) says it.
    hasScreenshots: (project.submissions[0]?.screenshots ?? 0) > 0,
  };
}

export function toDetailView(project: ProjectOut): ProjectDetailView {
  const drafts = project.drafts.map((draft) => ({ raw: draft, view: toDraft(draft) }));
  const entryItem = drafts.find((draft) => draft.raw.kind === "profile_entry");
  const entry = entryItem?.raw.entry;
  return {
    id: project.id,
    title: project.title,
    status: project.status,
    brief: project.brief
      ? {
          title: project.brief.title,
          objective: project.brief.objective,
          context: project.brief.context,
          constraints: project.brief.constraints,
          criteria: project.brief.criteria,
          deliverable: project.brief.deliverable,
          hours: project.brief.hours,
        }
      : null,
    evaluation: toEvaluation(project),
    submissions: project.submissions.map((submission, position) => ({
      at: submission.at,
      repoUrl: submission.repo_url,
      description: submission.description,
      screenshots: Array.from({ length: submission.screenshots }, (_, index) => ({
        number: index + 1,
        // The latest submission is « 1 » for the server, the one before « 2 »…
        src: screenshotUrl(project.id, index + 1, position + 1),
      })),
    })),
    drafts: drafts.flatMap(({ raw, view }) =>
      raw.kind === "profile_entry" ? [] : [{ ...view, kind: raw.kind }],
    ),
    entryDraft: entryItem?.view ?? null,
    entry: entry
      ? { name: entry.name, description: entry.description, achievements: entry.achievements ?? [] }
      : { name: project.title, description: "", achievements: [] },
    validatedAt: project.validated_at,
    profileVersion: project.profile_version,
    sessionId: project.session_id,
  };
}
