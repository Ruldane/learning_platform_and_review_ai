import { describe, expect, it } from "vitest";
import type { FeedItem } from "@/shared/realtime/types";
import { announcementOf, isFinishing, questionPosition } from "./questionPosition";

const turn = (messageId: string): FeedItem => ({
  kind: "turn",
  messageId,
  agent: "interviewer",
  text: "Une question",
  streaming: false,
  tools: [],
  citations: [],
});

const ask = (seq: number, id = `q${seq}`): Extract<FeedItem, { kind: "interrupt" }> => ({
  kind: "interrupt",
  seq,
  answered: false,
  interrupt: {
    interrupt_id: id,
    kind: "interview_answer",
    question: `Texte de la question ${seq} ?`,
    options: [],
  },
});

describe("questionPosition", () => {
  it("is the number of the last question asked before the interrupt", () => {
    const first = ask(2);
    const second = ask(5);
    const feed = [turn("interviewer-q1"), first, turn("interviewer-q2"), second];
    expect(questionPosition(feed, first)).toEqual({ number: 1, followUp: false });
    expect(questionPosition(feed, second)).toEqual({ number: 2, followUp: false });
  });

  it("recognises a follow-up by its message id", () => {
    const second = ask(5);
    const feed = [
      turn("interviewer-q1"),
      turn("interviewer-q2"),
      turn("interviewer-q2-relance"),
      second,
    ];
    expect(questionPosition(feed, second)).toEqual({ number: 2, followUp: true });
  });

  it("keeps the number when the same question is asked again after an unreadable answer", () => {
    const again = ask(7, "q-again");
    const feed = [turn("interviewer-q3"), ask(4), again];
    expect(questionPosition(feed, again)).toEqual({ number: 3, followUp: false });
  });

  it("is unknown when no question message came before", () => {
    const only = ask(1);
    expect(questionPosition([only], only)).toBeNull();
    expect(questionPosition([turn("other"), only], only)).toBeNull();
  });
});

describe("announcementOf", () => {
  it("announces the question with its number and its text", () => {
    const pending = ask(2);
    const feed = [turn("interviewer-q2"), pending];
    expect(announcementOf(feed, pending.interrupt, 7)).toBe(
      "Question 2 of 7. Texte de la question 2 ?",
    );
  });

  it("announces a follow-up as such", () => {
    const pending = ask(3);
    const feed = [turn("interviewer-q2"), turn("interviewer-q2-relance"), pending];
    expect(announcementOf(feed, pending.interrupt, 7)).toBe(
      "Follow-up on question 2. Texte de la question 3 ?",
    );
  });

  it("is empty with no question to answer, or for another kind of question", () => {
    expect(announcementOf([], null, 7)).toBe("");
    const other = { ...ask(2).interrupt, kind: "choice" };
    expect(announcementOf([], other, 7)).toBe("");
  });
});

describe("isFinishing", () => {
  const answered = (seq: number) => ({ ...ask(seq), answered: true });

  it("is true once the answer to the last question is sent, or the interview is stopped", () => {
    const feed = [turn("interviewer-q4"), answered(5)];
    expect(isFinishing(feed, null, 4, false)).toBe(true);
    expect(isFinishing([turn("interviewer-q1"), answered(2)], null, 4, true)).toBe(true);
  });

  it("is false before the last question, while a question is open, and with nothing asked", () => {
    expect(isFinishing([turn("interviewer-q2"), answered(3)], null, 4, false)).toBe(false);
    const open = ask(5);
    expect(isFinishing([turn("interviewer-q4"), open], open.interrupt, 4, true)).toBe(false);
    expect(isFinishing([], null, 4, false)).toBe(false);
  });
});
