import { api } from "@/shared/api/client";
import { unwrap } from "@/shared/api/errors";
import type { components } from "@/shared/api/schema";

export type MobileCard = Pick<components["schemas"]["FlashcardOut"], "id" | "front" | "back"> & {
  due: string;
};
export type Answer = components["schemas"]["ReviewIn"]["result"];

export interface MobileSnapshot {
  owner: string;
  day: string;
  lesson: string | null;
  minutes: number | null;
  offers: string[];
  cards: MobileCard[];
}

export interface QueuedReview {
  owner: string;
  id: string;
  card: string;
  due: string;
  result: Answer;
}

export async function verifyMobileAccount(signal?: AbortSignal) {
  return unwrap(await api.GET("/auth/me", { signal })).id;
}

export async function readUpcomingEvent(signal: AbortSignal) {
  return (await api.GET("/calendar/upcoming", { signal, cache: "no-store" })).data ?? null;
}

export async function loadMobile(owner: string, signal?: AbortSignal): Promise<MobileSnapshot> {
  const [brief, queue] = await Promise.all([
    api.GET("/brief/today", { signal }).then(unwrap),
    api.GET("/flashcards/due", { signal }).then(unwrap),
  ]);
  return {
    owner,
    day: brief.day,
    lesson: brief.block?.lesson_title ?? null,
    minutes: brief.block?.minutes ?? null,
    offers: brief.offers.items.flatMap(({ title }) => title ? [title] : []),
    cards: queue.cards.flatMap(({ id, front, back, due_date }) =>
      due_date ? [{ id, front, back, due: due_date }] : []),
  };
}

export async function sendReview(review: QueuedReview) {
  return unwrap(await api.POST("/flashcards/{card_id}/review", {
    params: { path: { card_id: review.card } },
    body: { result: review.result, receipt: { id: review.id, due_date: review.due } },
  }));
}
