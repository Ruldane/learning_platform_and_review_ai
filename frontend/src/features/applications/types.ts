/**
 * Types de vue des candidatures. Ils vivent à côté des composants (`components/viewTypes.ts`, qui
 * ne peuvent importer que leur propre dossier) ; les pages (7.13) les importent d'ici.
 */
export { MAX_CONTACTS, STATUS_ORDER } from "./components/viewTypes";
export type {
  ApplicationView,
  ChannelView,
  ContactView,
  DayString,
  EventKindView,
  EventView,
  ReminderKindView,
  ReminderView,
  StatsView,
  StatusView,
} from "./components/viewTypes";
