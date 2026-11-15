import type { components } from "@/shared/api/schema";
import type { KitPieceView } from "./components/viewTypes";

type Schemas = components["schemas"];

/** Les formes du serveur : seules `toView.ts`, `api.ts` et les hooks les manipulent. */
export type ApplicationOut = Schemas["ApplicationOut"];
export type ApplicationDetail = Schemas["ApplicationDetail"];
export type ApplicationIn = Schemas["ApplicationIn"];
export type ApplicationPatch = Schemas["ApplicationPatch"];
export type ApplicationStatsOut = Schemas["ApplicationStatsOut"];
export type AlertOut = Schemas["AlertOut"];
export type ContactIn = Schemas["ContactIn"];
export type ContactOut = Schemas["ContactOut"];
export type CreatedOut = Schemas["CreatedOut"];
export type EventIn = Schemas["EventIn"];
export type EventOut = Schemas["EventOut"];
export type KitItemOut = Schemas["KitItemOut"];
export type KitOut = Schemas["KitOut"];
export type InterviewIn = Schemas["InterviewIn"];
export type InterviewOut = Schemas["InterviewOut"];
export type ExchangeOut = Schemas["ExchangeOut"];
export type DebriefOut = Schemas["DebriefOut"];
export type FreeInterviewIn = Schemas["FreeInterviewIn"];
export type PostingSummaryOut = Schemas["PostingSummaryOut"];
export type ReminderOut = Schemas["ReminderOut"];

/** Le kit lu : la session ouverte (sinon la dernière), si elle tourne, les sept pièces dans l'ordre. */
export interface KitView {
  sessionId: string | null;
  running: boolean;
  pieces: KitPieceView[];
}

/**
 * Types de vue des candidatures. Ils vivent à côté des composants (`components/viewTypes.ts`, qui
 * ne peuvent importer que leur propre dossier) ; les pages (7.13) les importent d'ici.
 */
export {
  CHANNEL_ORDER,
  INTERVIEW_DURATIONS,
  INTERVIEW_LANGUAGES,
  INTERVIEW_MODES,
  KIT_KINDS,
  MAX_CONTACTS,
  SCORE_KEYS,
  STATUS_ORDER,
} from "./components/viewTypes";
export type {
  ApplicationView,
  ChannelView,
  ConfirmationFieldView,
  ConfirmationOptionView,
  ConfirmationView,
  ContactView,
  DebriefDataView,
  DayString,
  EventKindView,
  EventView,
  ExchangeView,
  ExpectedView,
  InterviewDurationView,
  InterviewLanguageView,
  InterviewModeView,
  InterviewStatusView,
  InterviewView,
  KitKindView,
  KitPieceView,
  KitSaveResult,
  KitSourceView,
  KitStatusView,
  ReminderKindView,
  ReminderView,
  ScoreKeyView,
  StatsView,
  StatusView,
} from "./components/viewTypes";
