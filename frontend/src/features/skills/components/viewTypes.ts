/** View types of the skill-map components: independent of the API contract (D34). */

/** Mastery level of a skill; `null`: no `user_skills` row (absent). */
export type LevelView = "declared" | "in_progress" | "validated" | "proven" | null;

export interface SkillNodeView {
  id: string;
  name: string;
  domain: string;
  level: LevelView;
  /**
   * Market demand, from 0 to 1; `null` until the market analysis has run (phase 8):
   * the node then keeps an average size.
   */
  demand: number | null;
  evidenceCount: number;
}

/** A prerequisite link: `beforeId` is learned before `afterId`. */
export interface SkillEdgeView {
  beforeId: string;
  afterId: string;
}

/** Score of a domain, from 0 to 100. */
export interface DomainScoreView {
  domain: string;
  score: number;
}

/** Number of skills at each level (level keys, without « absent »). */
export type LevelCounts = Record<Exclude<LevelView, null>, number>;

/** A weekly reading. */
export interface HistoryPointView {
  /** Monday of the week, `AAAA-MM-JJ`. */
  weekStart: string;
  counts: LevelCounts;
  /** 0 to 100. */
  score: number;
}

export interface EvidenceView {
  /** Kind of evidence: `lesson`, `quiz`, `study`, `program`, `capture`… */
  kind: string;
  label: string;
  /** ISO date of the evidence; `null` for old evidence (phase 4), shown without a date. */
  at: string | null;
  /** Path in the application; `null` when the evidence has no page. */
  url: string | null;
}

/** Offer that requires the skill (phase 6); the list is empty until then. */
export interface PostingRefView {
  id: string;
  title: string;
  url: string | null;
}

export interface NextActionView {
  kind: "study" | "quiz" | "review" | "project";
  label: string;
  /** `null` when the action is not yet available (proof project, phase 8). */
  url: string | null;
}

export interface SkillDetailView {
  id: string;
  name: string;
  domain: string;
  synonyms: string[];
  level: LevelView;
  evidence: EvidenceView[];
  postings: PostingRefView[];
  nextAction: NextActionView | null;
}

export interface CompareRowView {
  skillId: string;
  name: string;
  domain: string;
  /** Mon niveau ; `null` : absente. */
  mine: LevelView;
  /** Level expected by the target. */
  target: Exclude<LevelView, null>;
  /** Rank gap between the target and me (absent = −1); 0 or less: reached. */
  gap: number;
}

export type SkillViewId = "graph" | "radar" | "progress" | "compare";

/** What is compared against: the goal's target role, or an added offer. */
export type CompareTargetView = "goal" | "posting";

/** An analyzed offer, offered as the comparison target. */
export interface PostingChoiceView {
  id: string;
  title: string;
  company: string | null;
}
