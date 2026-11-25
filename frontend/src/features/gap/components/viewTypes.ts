/** View types for the posting and gap components: independent of the API contract (D34). */
import type { DuplicateAlertView } from "@/shared/ui/DuplicateAlert";

/** Mastery level of a skill; `null`: no row (absent). */
export type SkillLevelView = "declared" | "in_progress" | "validated" | "proven";

export type DuplicateLevel = "certain" | "probable" | "possible";

export interface DuplicateView {
  level: DuplicateLevel;
  postingId: string;
  title: string | null;
  company: string | null;
  /** ISO instant when the already known posting was added. */
  createdAt: string;
}

export type GapActionView = "in_program" | "to_add" | "out_of_scope";

/** Where the row comes from: the posting itself, or a keyword the CV review sent to the gap. */
export type GapSourceView = "posting" | "cv_review";

export interface GapRowView {
  skill: string;
  required: boolean;
  level: SkillLevelView | null;
  action: GapActionView;
  /** Week of the module's first task, for `in_program`. */
  week: number | null;
  source: GapSourceView;
}

/**
 * The row can be added to the planning: it is « À ajouter » and really missing (a
 * skill already validated or proven does not need learning).
 */
export function isAddable(row: GapRowView): boolean {
  return row.action === "to_add" && row.level !== "validated" && row.level !== "proven";
}

export function canPlan(row: GapRowView): boolean {
  return isAddable(row) || row.action === "out_of_scope";
}

export interface MissingSkillView {
  skill: string;
  /** Number of postings where the skill is missing. */
  postings: number;
  /** Among them, the number of postings that require it. */
  requiredIn: number;
}

export interface PostingAnalysisView {
  title: string;
  company: string | null;
  /** Seniority code from the analysis. Unknown codes use the unspecified label. */
  level: string;
  location: string | null;
  remote: string | null;
  requirements: { text: string; required: boolean }[];
  keywords: string[];
  eliminatory: string[];
  tools: string[];
}

/** What January provides to add a posting: a link or pasted text, never both. */
export type PostingSourceView = { url: string } | { text: string };

/** A submission error: API `code` (`posting_unreadable`…) and a message already in French. */
export interface FormErrorView {
  code: string;
  message: string;
}

/** Maximum number of skills added to the planning in a single submission. */
export const MAX_PLAN_SKILLS = 10;

export type PostingStatusView = "analyzing" | "ready" | "rejected" | "failed";

/** A row of the postings list. */
export interface PostingListItemView {
  id: string;
  /** `null` until the analysis has found the title. */
  title: string | null;
  company: string | null;
  /** Match score from 0 to 100; `null` until the gap is computed. */
  score: number | null;
  status: PostingStatusView;
}

/** The application that already exists for a posting. */
export interface ExistingApplicationView {
  id: string;
  company: string;
  title: string;
  status: DuplicateAlertView["status"];
}
