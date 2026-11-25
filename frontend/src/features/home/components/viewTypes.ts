/**
 * View types for home: a trimmed copy of what `GET /brief/today`
 * (`BriefOut`) and `GET /activity` (`ActivityPage`) return, with only the fields components
 * read. The pages (8.13) convert the responses into these shapes.
 */

export interface BlockTaskView {
  title: string;
  minutes: number;
}

/** `BlockRubric`: today's lesson, its tasks due and their total in minutes. */
export interface BlockView {
  moduleTitle: string;
  lessonTitle: string;
  minutes: number;
  tasks: BlockTaskView[];
}

/** `ReminderItem`: one reminder due. */
export interface ReminderItemView {
  id: string;
  applicationId: string;
  company: string;
  title: string;
  /** Jour `AAAA-MM-JJ`. */
  dueOn: string;
}

/** `OfferItem`: a new radar offer (score of at least 70). */
export interface OfferItemView {
  title: string | null;
  company: string | null;
  score: number;
  url: string;
  gapPath?: string;
}

/** `WeekRubric`: the progress of the program's week. */
export interface WeekView {
  doneMinutes: number;
  plannedMinutes: number;
  streakDays: number;
  tasksDone: number;
  tasksTotal: number;
}

/** `BriefResourceOut`: today's resource. `published`: a day or an ISO instant. */
export interface ResourceView {
  title: string;
  domain: string;
  published: string | null;
  why: string;
  url: string;
}

/** `advice_status`: `failed` and `unavailable` are final for the day (no « Réessayer »). */
export type AdviceStatus = "pending" | "ready" | "failed" | "unavailable";

export type ActivityKind = "lesson" | "radar" | "brief" | "memory" | "project" | "job_failed";

/** `ActivityItem`: `link` is a front-end route. */
export interface ActivityItemView {
  id: string;
  kind: ActivityKind;
  /** Instant ISO. */
  at: string;
  title: string;
  detail: string | null;
  link: string | null;
}

/** A background notification: an activity event that January has not seen yet. */
export interface NoticeView {
  id: string;
  title: string;
  detail?: string | null;
}
