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

/** Les six canaux de candidature, dans l'ordre des listes déroulantes. */
export const CHANNEL_ORDER = [
  "company_site",
  "job_board",
  "linkedin",
  "email",
  "referral",
  "other",
] as const;

export type ChannelView = (typeof CHANNEL_ORDER)[number];

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

/** Un champ pré rempli de la confirmation d'une fiche lue dans une phrase. */
export interface ConfirmationFieldView {
  id: string;
  label: string;
  required: boolean;
  maxLength: number;
  value: string;
}

/** Une issue proposée par le serveur (`create`, `distinct`, `open`, `cancel`). */
export interface ConfirmationOptionView {
  value: string;
  label: string;
}

/** La question « Je crée cette fiche ? » de l'Assistant de suivi, avec la fiche telle qu'il l'a lue. */
export interface ConfirmationView {
  question: string;
  fields: ConfirmationFieldView[];
  options: ConfirmationOptionView[];
  /** Pourquoi la question est reposée (la réponse précédente n'a pas pu être prise), s'il y a lieu. */
  reason?: string | null;
}

/** Les sept pièces du kit, dans l'ordre où le serveur les rend. */
export const KIT_KINDS = [
  "cv",
  "letter",
  "linkedin",
  "followups",
  "form_answers",
  "company_brief",
  "pitch",
] as const;
export type KitKindView = (typeof KIT_KINDS)[number];

/** `pending` : pas encore rangée ; `to_check` : à relire avant usage ; `failed` : non produite. */
export type KitStatusView = "pending" | "ready" | "to_check" | "failed";

/** Une page lue pour le dossier de l'entreprise ; `rank` est son numéro `[n]` dans le texte. */
export interface KitSourceView {
  rank: number;
  url: string;
  title: string | null;
}

/** Une pièce du kit telle que la page la montre. */
export interface KitPieceView {
  kind: KitKindView;
  status: KitStatusView;
  content: string;
  /** Les termes que le profil ne dit pas (pièce « à vérifier »). */
  flags: string[];
  /** Les réponses salariales laissées à January. */
  salaryFields: number;
  words: number | null;
  sources: KitSourceView[];
  /** January l'a modifiée : un nouveau lancement du kit la garde telle quelle. */
  edited: boolean;
  /** Le motif lisible d'une pièce en échec. */
  error: string | null;
  updatedAt: string | null;
}

/** Ce que l'enregistrement d'une modification rend à la pièce : le nouveau statut, ou le refus. */
export type KitSaveResult = { ok: true; status: KitStatusView } | { ok: false; message: string };

/** Les quatre formules d'entretien. */
export const INTERVIEW_MODES = ["behavioral", "technical", "case", "mixed"] as const;
export type InterviewModeView = (typeof INTERVIEW_MODES)[number];

/** Les trois durées : 4, 7 ou 10 questions principales. */
export const INTERVIEW_DURATIONS = [15, 30, 45] as const;
export type InterviewDurationView = (typeof INTERVIEW_DURATIONS)[number];

export const INTERVIEW_LANGUAGES = ["fr", "en"] as const;
export type InterviewLanguageView = (typeof INTERVIEW_LANGUAGES)[number];

/**
 * `running` : en cours ; `done` : débrief écrit ; `stopped` : arrêté avant toute réponse ;
 * `debrief_failed` : réponses gardées, débrief non écrit ; `failed` : session finie sans résultat.
 */
export type InterviewStatusView = "running" | "done" | "stopped" | "debrief_failed" | "failed";

/** Les quatre notes du débrief, dans l'ordre où elles s'affichent. */
export const SCORE_KEYS = ["clarte", "structure", "profondeur_technique", "adequation"] as const;
export type ScoreKeyView = (typeof SCORE_KEYS)[number];

/** Une question de l'entretien, la réponse de January, la relance éventuelle et la note (1 à 5). */
export interface ExchangeView {
  index: number;
  question: string;
  answer: string;
  followUp: string | null;
  followUpAnswer: string | null;
  note: number;
  /** Le modèle n'a pas pu noter cette réponse : la note n'est pas à lire. */
  unrated: boolean;
}

/** Les points qu'une bonne réponse à la question `index` aurait donnés. */
export interface ExpectedView {
  index: number;
  points: string[];
}

export interface DebriefDataView {
  scores: { key: ScoreKeyView; value: number }[];
  strengths: string[];
  fixes: string[];
  weakestIndex: number;
  improvedAnswer: string;
  /** Les questions de note 2 au plus, celles dont une fiche de révision est faite. */
  missed: number[];
  expected: ExpectedView[];
  /** Les questions que le modèle n'a pas pu noter. */
  unrated: number[];
}

/** Un entretien blanc tel que les pages le montrent. */
export interface InterviewView {
  id: string;
  applicationId: string | null;
  postingId: string | null;
  role: string | null;
  mode: InterviewModeView;
  durationMin: InterviewDurationView;
  /** Le nombre de questions principales (4, 7 ou 10 selon la durée). */
  questionCount: number;
  language: InterviewLanguageView;
  sessionId: string;
  status: InterviewStatusView;
  exchanges: ExchangeView[];
  debrief: DebriefDataView | null;
  /** Les termes que le profil ne dit pas dans la réponse améliorée. */
  flags: string[];
  cardsCreated: number;
  createdAt: string;
}

/** Les quatre personas du comité, dans l'ordre où le comité les nomme. */
export const PERSONA_ORDER = ["ats_reader", "recruiter", "manager", "colleague"] as const;

export type PersonaView = (typeof PERSONA_ORDER)[number];

export type VoteValueView = "oui" | "non" | "peut_etre";

export type CommitteeStatusView = "running" | "done" | "failed" | "stopped";

/** Le vote motivé d'une persona, avec son objection principale. */
export interface VoteView {
  persona: PersonaView;
  vote: VoteValueView;
  objection: string;
  reason: string;
}

/** Une objection du comité, classée (la première est la plus importante) ; `personas` : qui la soulève. */
export interface ObjectionView {
  text: string;
  personas: PersonaView[];
}

/** Un changement proposé ; `needsSkill` : il demande une compétence que le profil ne dit pas. */
export interface ChangeView {
  text: string;
  persona: PersonaView;
  needsSkill: boolean;
  terms: string[];
}

/** Le vote d'une persona à l'exécution précédente et à celle-ci. */
export interface VoteChangeView {
  persona: PersonaView;
  before: VoteValueView;
  after: VoteValueView;
}

/** L'avant et l'après : ce que la précédente exécution disait, ce qui a changé depuis. */
export interface CommitteeDiffView {
  votes: VoteChangeView[];
  resolved: string[];
  added: string[];
}

/** Une exécution du comité telle que la page la montre. */
export interface CommitteeView {
  id: string;
  cvVersionId: string;
  postingId: string;
  sessionId: string;
  status: CommitteeStatusView;
  verdict: VoteValueView | null;
  votes: VoteView[];
  objections: ObjectionView[];
  changes: ChangeView[];
  /** `null` : première exécution de l'offre (ou pas terminée). */
  diff: CommitteeDiffView | null;
}
