import type { ComponentProps } from "react";
import type { DebateFeed, InterruptCard } from "@/shared/session-ui";

/** View types of the capture and the journal: independent of the API contract (D34). */

/** Thread items and a card's question, as the session components read them. */
export type FeedItems = ComponentProps<typeof DebateFeed>["items"];
export type QuestionView = ComponentProps<typeof InterruptCard>["interrupt"];

export type JournalKindView =
  "capture" | "study_session" | "quiz" | "weekly_review" | "project" | "ide_check";

/** What the capture receives: a link or a note (the file takes its own path). */
export type CaptureSource = { kind: "url"; url: string } | { kind: "text"; text: string };

export interface JournalEntryView {
  id: string;
  kind: JournalKindView;
  text: string;
  /** Day of the entry, `AAAA-MM-JJ`. */
  occurredOn: string;
  /** Linked study session, to go back to it; `null` otherwise. */
  studySessionPath: string | null;
  practicePath?: string;
  /** Linked memory item; `null` otherwise. */
  memoryItemId: string | null;
}

/** The entries of one week (Monday to Sunday), weekly reviews first. */
export interface JournalWeekView {
  /** Monday of the week, `AAAA-MM-JJ`. */
  weekStart: string;
  entries: JournalEntryView[];
}
