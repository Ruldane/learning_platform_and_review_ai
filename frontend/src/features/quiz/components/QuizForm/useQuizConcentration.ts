import { useRef } from "react";
import type { ResponseTiming } from "@/shared/lib/concentration";
import { useResponseClock } from "@/shared/lib/useResponseClock";
import type { AnswerDraft } from "../viewTypes";
import type { Given } from "./useQuizAnswers";

export function useQuizConcentration(enabled: boolean) {
  const clock = useResponseClock(enabled);
  const first = useRef(new Map<string, number | null>());
  const typed = useRef<string | null>(null);
  const seal = (id: string) => first.current.set(id, clock.take());
  return {
    activity: () => clock.activity(),
    record(id: string, patch: Partial<Given>) {
      if (first.current.has(id)) return;
      if (patch.choice != null) seal(id);
      else if (patch.text !== undefined) typed.current = patch.text.trim() ? id : null;
    },
    leave(id: string) {
      if (typed.current === id) {
        seal(id);
        typed.current = null;
      }
    },
    timings(drafts: AnswerDraft[]): ResponseTiming[] {
      if (typed.current !== null) {
        seal(typed.current);
        typed.current = null;
      }
      const answered = new Set(
        drafts
          .filter((draft) => draft.choice !== null || draft.text)
          .map((draft) => draft.question_id),
      );
      return [...first.current].flatMap(([id, milliseconds]) =>
        answered.has(id) && milliseconds !== null ? [{ id, milliseconds }] : [],
      );
    },
  };
}
