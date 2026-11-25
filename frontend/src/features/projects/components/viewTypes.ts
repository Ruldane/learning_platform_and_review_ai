/**
 * View types for the mini projects: a reduced copy of `ProjectSummary`, `ProjectOut`,
 * `ProjectBriefOut`, `EvaluationOut`, `CriterionOut` and `DraftOut` (`contracts/openapi.json`) with
 * only the fields the components read. The pages (8.15) convert the responses.
 */

export const PROJECT_STATUSES = [
  "brief_pending",
  "brief_failed",
  "todo",
  "reviewing",
  "to_redo",
  "validated",
] as const;

export type ProjectStatusView = (typeof PROJECT_STATUSES)[number];

/** `ProjectSummary`: a Portfolio card. */
export interface ProjectCardView {
  id: string;
  title: string;
  status: ProjectStatusView;
  /** Estimated hours from the brief; `null` until it is written. */
  hours: number | null;
  skills: string[];
  /** The project page's address; without it, the title is not a link. */
  href?: string;
}

export type DeliverableView = "repo" | "description" | "either";

/** `ProjectBriefOut`: the brief written by the Practitioner. */
export interface BriefDataView {
  title: string;
  objective: string;
  context: string;
  constraints: string[];
  criteria: string[];
  deliverable: DeliverableView;
  hours: number;
}

/** `CriterionOut`: a criterion's result. `index` counts from 1. */
export interface CriterionResultView {
  index: number;
  met: boolean;
  comment: string;
}

export type RepoStatusView = "read" | "unreadable" | "none";

/** `EvaluationOut`: the latest evaluation; the verdict is computed by the code. */
export interface EvaluationDataView {
  verdict: "validated" | "to_redo";
  feedback: string;
  repoStatus: RepoStatusView;
  /** The Practitioner's results: each links to a brief criterion by its `index`, not by place. */
  results: CriterionResultView[];
  /** The last submission had screenshots, never read by the Practitioner; the page derives it. */
  hasScreenshots: boolean;
}

/** What the submission form sends: at least one link or a description. */
export interface SubmissionView {
  repoUrl: string | null;
  description: string | null;
  screenshots: File[];
  githubClaimId?: string;
}

export interface GithubCommitSelection {
  repoUrl: string;
  sha: string;
}

export interface GithubClaimView extends GithubCommitSelection {
  id: string;
  code: string;
  profileUrl: string;
}

export interface GithubClaimForm {
  request: (selection: GithubCommitSelection) => void;
  pending: boolean;
  error: string | null;
  claim: GithubClaimView | null;
}

export type DraftKindView = "cv_line" | "profile_entry" | "linkedin_post" | "readme_plan";

/** `DraftOut`: a draft in January's name. `flags`: terms its profile and submission do not back. */
export interface DraftView {
  kind: DraftKindView;
  content: string;
  status: "ready" | "to_check";
  flags: string[];
  edited: boolean;
}

/** `ProfileEntryIn`: the project entry proposed for the master profile. */
export interface ProfileEntryView {
  name: string;
  description: string;
  achievements: string[];
}

/** The submission fields the server refuses (422), each with its message; never a value. */
export interface SubmissionRefusalView {
  missing?: string;
  repoUrl?: string;
  description?: string;
  screenshots?: string;
}
