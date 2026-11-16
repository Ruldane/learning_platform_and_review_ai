/**
 * Types de vue des mini projets : une copie réduite de `ProjectSummary`, `ProjectOut`,
 * `ProjectBriefOut`, `EvaluationOut`, `CriterionOut` et `DraftOut` (`contracts/openapi.json`) avec
 * les seuls champs que les composants lisent. Les pages (8.15) convertissent les réponses.
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

/** `ProjectSummary` : une carte du Portfolio. */
export interface ProjectCardView {
  id: string;
  title: string;
  status: ProjectStatusView;
  /** Heures estimées par l'énoncé ; `null` tant qu'il n'est pas écrit. */
  hours: number | null;
  skills: string[];
  /** L'adresse de la page du projet ; sans elle, le titre n'est pas un lien. */
  href?: string;
}

export type DeliverableView = "repo" | "description" | "either";

/** `ProjectBriefOut` : l'énoncé écrit par le Praticien. */
export interface BriefDataView {
  title: string;
  objective: string;
  context: string;
  constraints: string[];
  criteria: string[];
  deliverable: DeliverableView;
  hours: number;
}

/** `CriterionOut` : le résultat d'un critère. `index` compte à partir de 1. */
export interface CriterionResultView {
  index: number;
  met: boolean;
  comment: string;
}

export type RepoStatusView = "read" | "unreadable" | "none";

/** `EvaluationOut` : la dernière évaluation ; le verdict est calculé par le code. */
export interface EvaluationDataView {
  verdict: "validated" | "to_redo";
  feedback: string;
  repoStatus: RepoStatusView;
  /** Les critères avec leur résultat (le texte du critère accompagne chaque résultat). */
  results: (CriterionResultView & { criterion: string })[];
  /** Le rendu évalué comportait des captures (jamais lues par le Praticien). */
  hasScreenshots: boolean;
}

/** Ce que le formulaire de rendu remet : au moins un lien ou une description. */
export interface SubmissionView {
  repoUrl: string | null;
  description: string | null;
  screenshots: File[];
}

export type DraftKindView = "cv_line" | "profile_entry" | "linkedin_post" | "readme_plan";

/** `DraftOut` : un brouillon au nom de January. `flags` : les termes que son profil et son rendu ne disent pas. */
export interface DraftView {
  kind: DraftKindView;
  content: string;
  status: "ready" | "to_check";
  flags: string[];
  edited: boolean;
}

/** `ProfileEntryIn` : l'entrée de projet proposée pour le profil maître. */
export interface ProfileEntryView {
  name: string;
  description: string;
  achievements: string[];
}
