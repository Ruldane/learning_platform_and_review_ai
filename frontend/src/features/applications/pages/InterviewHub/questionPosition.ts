import { t } from "@/shared/i18n/t";
import type { FeedItem, InterruptPayload } from "@/shared/realtime/types";

/** The name of the question the server asks in writing (7.8). */
export const ANSWER_KIND = "interview_answer";

const QUESTION_MESSAGE = /^interviewer-q(\d+)(-relance)?$/;

export interface QuestionPosition {
  /** The rank of the main question, from 1. */
  number: number;
  followUp: boolean;
}

/**
 * The rank of the question the `item` interruption asks: the payload does not carry it, so the
 * last interviewer message (`interviewer-q<n>`, `-relance` for a follow-up) before it is read.
 * `null` until none has arrived. A re-asked question (unreadable answer) keeps its rank.
 */
export function questionPosition(feed: FeedItem[], item: FeedItem): QuestionPosition | null {
  let position: QuestionPosition | null = null;
  for (const entry of feed) {
    if (entry === item) return position;
    if (entry.kind !== "turn") continue;
    const match = QUESTION_MESSAGE.exec(entry.messageId);
    if (match) position = { number: Number(match[1]), followUp: match[2] !== undefined };
  }
  return position;
}

/** What the live region says of a new question: its rank and text; nothing if none. */
export function announcementOf(
  feed: FeedItem[],
  pending: InterruptPayload | null,
  total: number,
): string {
  if (pending === null || pending.kind !== ANSWER_KIND) return "";
  const item = feed.find(
    (entry) => entry.kind === "interrupt" && entry.interrupt.interrupt_id === pending.interrupt_id,
  );
  const position = item ? questionPosition(feed, item) : null;
  if (position === null) return pending.question;
  const lead = position.followUp
    ? t("applications.interviewRun.announceFollowUp", { number: position.number })
    : t("applications.interviewRun.announceQuestion", { number: position.number, total });
  return `${lead} ${pending.question}`;
}

/**
 * The interview no longer waits on January; the debrief is being written. January ended it,
 * or answered the last main question (a follow-up could still come: it would erase
 * this sentence). False while a question is open.
 */
export function isFinishing(
  feed: FeedItem[],
  pending: InterruptPayload | null,
  total: number,
  stopped: boolean,
): boolean {
  if (pending !== null) return false;
  const answers = feed.filter(
    (entry): entry is Extract<FeedItem, { kind: "interrupt" }> =>
      entry.kind === "interrupt" && entry.interrupt.kind === ANSWER_KIND,
  );
  const last = answers[answers.length - 1];
  if (!last?.answered) return false;
  if (stopped) return true;
  return (questionPosition(feed, last)?.number ?? 0) >= total;
}
