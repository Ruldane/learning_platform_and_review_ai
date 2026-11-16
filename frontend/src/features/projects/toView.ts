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

/** Une carte du Portfolio. */
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

/** Les groupes du Portfolio, dans l'ordre où ils s'affichent : ce qui attend January d'abord. */
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

/** Les projets groupés par statut ; un groupe vide n'existe pas, l'ordre du programme est gardé. */
export function groupByStatus(projects: ProjectCardView[]): ProjectGroupView[] {
  return GROUP_ORDER.flatMap((status) => {
    const inGroup = projects.filter((project) => project.status === status);
    return inGroup.length > 0 ? [{ status, projects: inGroup }] : [];
  });
}

/** Une capture d'un rendu, avec l'adresse de son image. */
export interface ShotView {
  number: number;
  src: string;
}

/** Un rendu de l'historique (le dernier d'abord). */
export interface SubmissionItemView {
  at: string;
  repoUrl: string | null;
  description: string | null;
  screenshots: ShotView[];
}

/** Un projet tel que sa page le lit. */
export interface ProjectDetailView {
  id: string;
  title: string;
  status: ProjectStatusView;
  brief: BriefDataView | null;
  evaluation: EvaluationDataView | null;
  submissions: SubmissionItemView[];
  /** Les brouillons de texte (ligne de CV, post LinkedIn, plan de README), dans l'ordre du serveur. */
  drafts: (DraftView & { kind: Exclude<DraftView["kind"], "profile_entry"> })[];
  /** Le brouillon de l'entrée du profil (son avertissement « à vérifier »), s'il existe. */
  entryDraft: DraftView | null;
  /** L'entrée proposée pour le profil maître : le brouillon, sinon le nom du projet seul. */
  entry: ProfileEntryView;
  validatedAt: string | null;
  profileVersion: number | null;
  /** La session de l'énoncé ou de l'évaluation en cours, sinon la dernière. */
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
    // `EvaluationOut` n'a pas ce champ : le dernier rendu (le premier de la liste) le dit.
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
        // Le dernier rendu est « 1 » pour le serveur, celui d'avant « 2 »…
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
