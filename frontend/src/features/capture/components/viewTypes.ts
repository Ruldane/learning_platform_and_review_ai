import type { ComponentProps } from "react";
import type { DebateFeed, InterruptCard } from "@/shared/session-ui";

/** Types de vue de la capture et du journal : indépendants du contrat d'API (D34). */

/** Les éléments du fil et la question d'une carte, tels que les composants de session les lisent. */
export type FeedItems = ComponentProps<typeof DebateFeed>["items"];
export type QuestionView = ComponentProps<typeof InterruptCard>["interrupt"];

export type JournalKindView = "capture" | "study_session" | "quiz" | "weekly_review";

/** Ce que la capture reçoit : un lien ou une note (le fichier passe par son propre chemin). */
export type CaptureSource = { kind: "url"; url: string } | { kind: "text"; text: string };

export interface JournalEntryView {
  id: string;
  kind: JournalKindView;
  text: string;
  /** Jour de l'entrée, `AAAA-MM-JJ`. */
  occurredOn: string;
  /** Session d'étude liée, pour y revenir ; `null` sinon. */
  studySessionId: string | null;
  /** Élément de mémoire lié ; `null` sinon. */
  memoryItemId: string | null;
}

/** Les entrées d'une semaine (lundi → dimanche), bilans hebdomadaires en tête. */
export interface JournalWeekView {
  /** Lundi de la semaine, `AAAA-MM-JJ`. */
  weekStart: string;
  entries: JournalEntryView[];
}
