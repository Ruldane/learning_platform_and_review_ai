import type { components } from "@/shared/api/schema";
import type { KitPieceView } from "./components/viewTypes";

type Schemas = components["schemas"];

/** The server shapes: only `toView.ts`, `api.ts` and the hooks handle them. */
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
export type CommitteeRunOut = Schemas["CommitteeRunOut"];
export type CvVersionOut = Schemas["VersionOut"];

/** The kit read: the open session (otherwise the latest), whether it runs, the seven pieces in
 * order. */
export interface KitView {
  sessionId: string | null;
  running: boolean;
  pieces: KitPieceView[];
}

/**
 * View types for applications. They live next to the components (`components/viewTypes.ts`, which
 * may only import their own folder); the pages (7.13) import them from here.
 */
export {
  CHANNEL_ORDER,
  INTERVIEW_DURATIONS,
  INTERVIEW_LANGUAGES,
  INTERVIEW_MODES,
  KIT_KINDS,
  MAX_CONTACTS,
  PERSONA_ORDER,
  SCORE_KEYS,
  STATUS_ORDER,
} from "./components/viewTypes";
export { isChannel, isStatus } from "./components/guards";
export type {
  ApplicationView,
  ChangeView,
  ChannelView,
  CommitteeDiffView,
  CommitteeStatusView,
  CommitteeView,
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
  ObjectionView,
  PersonaView,
  ReminderKindView,
  ReminderView,
  ScoreKeyView,
  StatsView,
  StatusView,
  VoteChangeView,
  VoteValueView,
  VoteView,
} from "./components/viewTypes";
