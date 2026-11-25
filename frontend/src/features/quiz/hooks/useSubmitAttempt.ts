import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import { createAttempt, type AnswerBody } from "../api";
import { dayOf } from "../toView";

/** Message for a refused send: too-early attempts give the date, others the back end message. */
export function submitErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === "retry_too_soon") {
    const day = dayOf((error.details as { retry_on?: string } | null)?.retry_on);
    if (day) return t("quiz.page.retryTooSoon", { date: longDay(day) });
  }
  return errorMessage(error);
}

/**
 * Sends a quiz's answers (`POST /quizzes/{id}/attempts`): returns the attempt identifier, or
 * `null` if the send is refused (the message is in `error`). One send at a time, set synchronously:
 * two clicks at the same instant send only one attempt. An accepted attempt keeps the lock until
 * `release` (back to the form, resend); `release` does nothing while a send is in flight: a double
 * click on « Renvoyer » sends only one.
 */
export function useSubmitAttempt(quizId: string) {
  const sending = useRef(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: ({ answers, elapsedMs }: { answers: AnswerBody[]; elapsedMs?: number }) =>
      createAttempt(quizId, answers, elapsedMs),
  });
  const { mutateAsync } = mutation;

  const submit = async (answers: AnswerBody[], elapsedMs?: number): Promise<string | null> => {
    if (sending.current) return null;
    sending.current = true;
    inFlight.current = true;
    setError(null);
    try {
      const started = await mutateAsync({ answers, elapsedMs });
      return started.attempt_id;
    } catch (failure) {
      setError(submitErrorMessage(failure));
      sending.current = false;
      return null;
    } finally {
      inFlight.current = false;
    }
  };
  const release = () => {
    if (inFlight.current) return;
    sending.current = false;
    setError(null);
  };
  return { submit, release, pending: mutation.isPending, error };
}
