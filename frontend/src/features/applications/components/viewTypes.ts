/**
 * Types de vue des composants des candidatures : indépendants du contrat d'API (D34). Les pages
 * (7.13) convertissent les réponses du serveur (`ApplicationOut`, `ReminderOut`, `EventOut`,
 * `ApplicationStatsOut`, `AlertOut`) vers ces formes.
 */

/** Les huit statuts, dans l'ordre des colonnes du tableau de suivi (`STATUS_ORDER` côté back). */
export const STATUS_ORDER = [
  "to_apply",
  "applied",
  "followed_up",
  "interview",
  "offer",
  "rejected",
  "no_answer",
  "withdrawn",
] as const;

export type StatusView = (typeof STATUS_ORDER)[number];

export type ChannelView =
  "company_site" | "job_board" | "linkedin" | "email" | "referral" | "other";

/** Un jour `AAAA-MM-JJ`. */
export type DayString = string;

/** Une fiche de candidature, telle que les cartes et le tableau l'affichent. */
export interface ApplicationView {
  id: string;
  company: string;
  title: string;
  status: StatusView;
  channel: ChannelView | null;
  appliedOn: DayString | null;
  interviewOn: DayString | null;
  nextAction: string | null;
  nextActionOn: DayString | null;
  /** Relances arrivées à échéance et pas encore traitées. */
  dueReminders: number;
}

/** Un contact d'une fiche ; `id` est vide pour un contact ajouté à la main, pas encore enregistré. */
export interface ContactView {
  id: string;
  name: string;
  role: string | null;
  url: string | null;
}

export type EventKindView =
  "created" | "status" | "note" | "reminder" | "kit" | "interview" | "committee" | "version";

/** Une ligne du fil chronologique ; `at` est un instant ISO. */
export interface EventView {
  id: string;
  kind: EventKindView;
  at: string;
  statusFrom: StatusView | null;
  statusTo: StatusView | null;
  text: string | null;
}

export type ReminderKindView = "linkedin_7" | "email_14" | "close_21" | "thanks" | "news_7";

/** Une relance à traiter : l'application n'envoie rien, January copie le brouillon. */
export interface ReminderView {
  id: string;
  applicationId: string;
  kind: ReminderKindView;
  dueOn: DayString;
  company: string;
  title: string;
  contact: ContactView | null;
  /** Recherche LinkedIn proposée quand la fiche n'a aucun contact. */
  linkedinSearchUrl: string | null;
  draft: string;
}

/** Les indicateurs ; `responseRate` est une part entre 0 et 1. */
export interface StatsView {
  byStatus: Record<StatusView, number>;
  responseRate: number | null;
  meanResponseDays: number | null;
  dueReminders: number;
}

export const MAX_CONTACTS = 10;
