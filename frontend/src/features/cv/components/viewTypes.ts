/** View types of the master profile components: independent of the API contract (D34). */

/** Where a fact comes from: the CV, LinkedIn, January's note, or January herself. */
export type FactSourceView = "cv" | "linkedin" | "note" | "january";

/** A line of profile text (achievement, detail, title, summary), with its stable id. */
export interface LineView {
  /** Empty for a line added by hand: the id is assigned on save. */
  id: string;
  text: string;
  /** Only the title and summary carry sources; they are sent back unchanged on save. */
  sources?: FactSourceView[];
}

export interface IdentityView {
  name: string;
  email: string | null;
  phone: string | null;
  location: string | null;
  headline: string | null;
}

export interface ExperienceView {
  id: string;
  role: string;
  company: string;
  location: string | null;
  /** « AAAA-MM » or « AAAA ». */
  start: string | null;
  end: string | null;
  achievements: LineView[];
  sources: FactSourceView[];
}

export interface EducationView {
  id: string;
  degree: string;
  school: string;
  start: string | null;
  end: string | null;
  details: LineView[];
  sources: FactSourceView[];
}

export interface SkillFactView {
  id: string;
  name: string;
  category: string | null;
  sources: FactSourceView[];
}

export interface ProjectView {
  id: string;
  name: string;
  description: string;
  link: string | null;
  achievements: LineView[];
  sources: FactSourceView[];
}

export interface LanguageView {
  id: string;
  name: string;
  level: string | null;
  sources: FactSourceView[];
}

export interface LinkView {
  id: string;
  label: string;
  url: string;
  sources: FactSourceView[];
}

/** The master profile: the only source of CV facts (mirror of `MasterProfileData`). */
export interface MasterProfileView {
  identity: IdentityView;
  title: LineView | null;
  summary: LineView | null;
  experiences: ExperienceView[];
  education: EducationView[];
  skills: SkillFactView[];
  projects: ProjectView[];
  languages: LanguageView[];
  links: LinkView[];
}

export type ProfileStatusView = "draft" | "validated";

export interface ProfileVersionView {
  version: number;
  status: ProfileStatusView;
  /** `archivist` (read from documents) or `january` (edited by her); other values pass through. */
  source: string;
  /** ISO instant of creation. */
  createdAt: string;
}

/** What January provides to create the profile: the CV as PDF, LinkedIn, and an optional note. */
export interface ProfileImportView {
  cv: File;
  linkedin?: File;
  note?: string;
}

/** A save error: the message, and the text to show under each faulty field, by its path. */
export interface ProfileSaveErrorView {
  message: string;
  /** Field path (`experiences.2.role`) → what to fix; never the entered value. */
  fields: Record<string, string>;
}

export const MAX_PDF_BYTES = 10 * 1024 * 1024;
export const MAX_NOTE_CHARS = 4000;

/** The sections of a targeted CV (mirror of `SectionKey`). */
export type CvSectionView =
  "summary" | "experience" | "education" | "skills" | "projects" | "languages" | "links";

export type ModificationStatusView = "proposed" | "to_confirm" | "accepted" | "refused";
export type ModificationActionView = "rewrite" | "add" | "remove" | "move";
export type ModificationTypeView = "keyword" | "clarity" | "impact" | "order" | "length" | "title";

/** What can be decided on a change: accept it or refuse it. */
export type DecisionView = "accepted" | "refused";

/** A decision sent to the back end: resolves to `false` when refused (the editor stays open). */
export type DecideResult = void | Promise<boolean>;

/** What January attaches to her decision: the text she edited, and the confirmation of a fact. */
export interface DecideOptions {
  after?: string;
  confirm?: boolean;
}

/** A master profile fact that a change relies on (G2, F4). */
export interface FactRefView {
  id: string;
  label: string;
}

/** A change proposed by the CV review. */
export interface ModificationView {
  id: string;
  ref: string;
  section: CvSectionView;
  action: ModificationActionView;
  type: ModificationTypeView;
  before: string;
  after: string;
  reason: string;
  status: ModificationStatusView;
  /** Why the change is « à confirmer »: a figure, a tool or a title missing from the profile. */
  blocks: string[];
  /** The slug of the agent that proposed it (`agentIdentity`). */
  author: string;
  facts: FactRefView[];
  /** The number of the generated version where this accepted change could not be placed. */
  ignoredIn?: number | null;
}

export const MAX_EDIT_CHARS = 600;

/**
 * A layout gap between the original and the recreated template: the ink share (0 to 1) of
 * each side, in one zone of the page.
 */
export interface ZoneView {
  zone: "top" | "middle" | "bottom" | "left" | "right";
  original: number;
  render: number;
}

export type AtsCheckIdView =
  "selectable_text" | "reading_order" | "standard_headings" | "contact_in_body" | "font_sizes";

export interface AtsCheckView {
  id: AtsCheckIdView;
  passed: boolean;
  /** One sentence in French, with no CV data. */
  detail: string;
}

/** The two indicators of a CV: requirements coverage and machine readability. */
export interface IndicatorsView {
  coveragePercent: number;
  covered: number;
  total: number;
  /** The mandatory requirements that the CV does not cover. */
  missing: string[];
  checks: AtsCheckView[];
}

export type VersionStatusView = "rendering" | "ready" | "pages_exceeded" | "failed";

export interface VersionView {
  id: string;
  number: number;
  status: VersionStatusView;
  pageCount: number | null;
  originalPageCount: number;
  filename: string;
  /** ISO instant of creation. */
  createdAt: string;
  failureReason: string | null;
}

/** The review report: what counts for and against this CV for this posting. */
export interface ReportView {
  /** The recognized applicant tracking software (« Greenhouse »), or `null`. */
  ats: string | null;
  atsNotes: string[];
  companySummary: string | null;
  strengths: string[];
  risks: string[];
  eliminatory: string[];
}
