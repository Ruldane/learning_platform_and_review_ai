/** View types of the lesson components: independent of the API contract (D34). */

/** View type of the lesson reader. */
export interface LessonView {
  title: string;
  markdown: string;
  wordCount: number;
  /** Address of the PDF, or `null` until it is ready. */
  pdfUrl: string | null;
}

export type ResourceType =
  | "documentation"
  | "course"
  | "video"
  | "article"
  | "repository"
  | "paper";
export type ResourceLevel = "beginner" | "intermediate" | "advanced";
export type ResourceStatus = "to_read" | "read";

export interface ResourceView {
  id: string;
  title: string;
  /** Web address (http or https only); `null` if the server address is not one. */
  url: string | null;
  type: ResourceType;
  /** Language code (`fr`, `en`…). */
  lang: string | null;
  durationMinutes: number | null;
  level: ResourceLevel | null;
  author: string | null;
  /** Publication date, as the source gives it. */
  date: string | null;
  /** The reason for the choice, in one sentence. */
  reason: string;
  /** Reading sheet (resource without a local copy). */
  note: string | null;
  /** Address of the local copy (PDF), if there is one. */
  localCopyUrl: string | null;
  status: ResourceStatus;
}

/** The library filters: `null` means "all". */
export interface LibraryFilterValue {
  programId: string | null;
  type: ResourceType | null;
  lang: string | null;
  status: ResourceStatus | null;
}

export interface ProgramOption {
  id: string;
  title: string;
}
