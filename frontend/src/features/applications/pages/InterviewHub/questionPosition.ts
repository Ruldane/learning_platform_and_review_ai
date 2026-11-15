import { t } from "@/shared/i18n/t";
import type { FeedItem, InterruptPayload } from "@/shared/realtime/types";

/** Le nom de la question que le serveur pose à l'écrit (7.8). */
export const ANSWER_KIND = "interview_answer";

const QUESTION_MESSAGE = /^interviewer-q(\d+)(-relance)?$/;

export interface QuestionPosition {
  /** Le rang de la question principale, à partir de 1. */
  number: number;
  followUp: boolean;
}

/**
 * Le rang de la question que pose l'interruption `item` : le payload ne le porte pas, on lit donc le
 * dernier message de l'intervieweur (`interviewer-q<n>`, `-relance` pour une relance) avant elle.
 * `null` tant qu'aucun n'est arrivé. Une question reposée (réponse illisible) garde son rang.
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

/** Ce que la zone vocale dit d'une nouvelle question : son rang et son texte ; rien sans question à répondre. */
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
 * L'entretien n'attend plus rien de January et le débrief va s'écrire : elle a terminé l'entretien,
 * ou répondu à la dernière question principale (une relance pourrait encore venir : elle effacerait
 * cette phrase). Faux tant qu'une question est ouverte.
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
