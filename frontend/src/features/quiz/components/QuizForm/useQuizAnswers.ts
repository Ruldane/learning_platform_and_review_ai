import { useMemo, useState } from "react";
import type { AnswerDraft, QuestionView } from "../viewTypes";

export interface Given {
  choice: number | null;
  text: string;
}

const NONE: Given = { choice: null, text: "" };

function isEmpty(question: QuestionView, given: Given): boolean {
  return question.type === "qcm" ? given.choice === null : given.text.trim() === "";
}

/** Les réponses saisies, les questions restées vides et le brouillon à envoyer, dans l'ordre. */
export function useQuizAnswers(questions: QuestionView[]) {
  const ordered = useMemo(() => [...questions].sort((a, b) => a.rank - b.rank), [questions]);
  const [answers, setAnswers] = useState<Record<string, Given>>({});

  const given = (id: string): Given => answers[id] ?? NONE;
  const change = (id: string, patch: Partial<Given>) =>
    setAnswers((current) => ({ ...current, [id]: { ...(current[id] ?? NONE), ...patch } }));
  const empties = ordered.filter((question) => isEmpty(question, given(question.id)));
  const drafts = (): AnswerDraft[] =>
    ordered.map((question) => {
      const answer = given(question.id);
      return { question_id: question.id, choice: answer.choice, text: answer.text.trim() };
    });

  return { ordered, given, change, empties, drafts };
}
