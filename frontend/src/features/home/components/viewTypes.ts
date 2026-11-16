/**
 * Types de vue de l'accueil : une copie réduite de ce que renvoient `GET /brief/today`
 * (`BriefOut`) et `GET /activity` (`ActivityPage`), avec les seuls champs que les composants
 * lisent. Les pages (8.13) convertissent les réponses vers ces formes.
 */

export interface BlockTaskView {
  title: string;
  minutes: number;
}

/** `BlockRubric` : la leçon du jour, ses tâches dues et leur total en minutes. */
export interface BlockView {
  moduleTitle: string;
  lessonTitle: string;
  minutes: number;
  tasks: BlockTaskView[];
}

/** `ReminderItem` : une relance due. */
export interface ReminderItemView {
  id: string;
  applicationId: string;
  company: string;
  title: string;
  /** Jour `AAAA-MM-JJ`. */
  dueOn: string;
}

/** `OfferItem` : une nouvelle offre du radar (score d'au moins 70). */
export interface OfferItemView {
  title: string | null;
  company: string | null;
  score: number;
  url: string;
}

/** `WeekRubric` : l'avancement de la semaine du programme. */
export interface WeekView {
  doneMinutes: number;
  plannedMinutes: number;
  streakDays: number;
  tasksDone: number;
  tasksTotal: number;
}

/** `BriefResourceOut` : la ressource du jour. `published` : un jour ou un instant ISO. */
export interface ResourceView {
  title: string;
  domain: string;
  published: string | null;
  why: string;
  url: string;
}

/** `advice_status` : `failed` et `unavailable` sont définitifs pour la journée (aucun « Réessayer »). */
export type AdviceStatus = "pending" | "ready" | "failed" | "unavailable";

export type ActivityKind = "lesson" | "radar" | "brief" | "memory" | "project" | "job_failed";

/** `ActivityItem` : `link` est une route du front. */
export interface ActivityItemView {
  id: string;
  kind: ActivityKind;
  /** Instant ISO. */
  at: string;
  title: string;
  detail: string | null;
  link: string | null;
}

/** Une notification de fond : un événement du fil d'activité que January n'a pas encore vu. */
export interface NoticeView {
  id: string;
  title: string;
  detail?: string | null;
}
