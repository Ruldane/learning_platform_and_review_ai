import { SCORE_KEYS } from "./types";
import type {
  DebriefDataView,
  DebriefOut,
  ExchangeOut,
  ExchangeView,
  InterviewOut,
  InterviewView,
} from "./types";

/** Les questions principales d'un entretien : 4 à 15 minutes, 7 à 30, 10 à 45 (7.9). */
const QUESTIONS: Record<InterviewOut["duration_min"], number> = { 15: 4, 30: 7, 45: 10 };

export const questionCount = (durationMin: InterviewOut["duration_min"]): number =>
  QUESTIONS[durationMin];

function toExchangeView(out: ExchangeOut): ExchangeView {
  return {
    index: out.index,
    question: out.question,
    answer: out.answer,
    followUp: out.follow_up,
    followUpAnswer: out.follow_up_answer,
    note: out.note,
    unrated: out.unrated,
  };
}

function toDebriefView(out: DebriefOut): DebriefDataView {
  return {
    scores: SCORE_KEYS.map((key) => ({ key, value: out.scores[key] ?? 0 })),
    strengths: out.strengths,
    fixes: out.fixes,
    weakestIndex: out.weakest_index,
    improvedAnswer: out.improved_answer,
    missed: out.missed,
    expected: out.expected.map(({ index, points }) => ({ index, points })),
    unrated: out.unrated,
  };
}

/** Un entretien du serveur → la vue des pages. */
export function toInterviewView(out: InterviewOut): InterviewView {
  return {
    id: out.id,
    applicationId: out.application_id,
    postingId: out.posting_id,
    role: out.role,
    mode: out.mode,
    durationMin: out.duration_min,
    questionCount: questionCount(out.duration_min),
    language: out.language,
    sessionId: out.session_id,
    status: out.status,
    exchanges: out.exchanges.map(toExchangeView),
    debrief: out.debrief ? toDebriefView(out.debrief) : null,
    flags: out.flags,
    cardsCreated: out.cards_created,
    createdAt: out.created_at,
  };
}
