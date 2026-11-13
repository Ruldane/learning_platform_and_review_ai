import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { longDay } from "@/shared/lib/format";
import { createAttempt, type AnswerBody } from "../api";
import { dayOf } from "../toView";

/** Message d'un envoi refusé : un essai trop tôt dit la date, les autres le message du back. */
export function submitErrorMessage(error: unknown): string {
  if (error instanceof ApiError && error.code === "retry_too_soon") {
    const day = dayOf((error.details as { retry_on?: string } | null)?.retry_on);
    if (day) return t("quiz.page.retryTooSoon", { date: longDay(day) });
  }
  return errorMessage(error);
}

/**
 * Envoi des réponses d'un quiz (`POST /quizzes/{id}/attempts`) : renvoie l'identifiant de la
 * tentative, ou `null` si l'envoi est refusé (le message est dans `error`). Un seul envoi à la
 * fois, posé de façon synchrone : deux clics dans le même instant n'envoient qu'une tentative. Une
 * tentative acceptée garde le verrou jusqu'à `release` (retour au formulaire, renvoi) ; `release`
 * ne fait rien tant qu'un envoi est en route : un double clic sur « Renvoyer » n'en part qu'un.
 */
export function useSubmitAttempt(quizId: string) {
  const sending = useRef(false);
  const inFlight = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (answers: AnswerBody[]) => createAttempt(quizId, answers),
  });
  const { mutateAsync } = mutation;

  const submit = async (answers: AnswerBody[]): Promise<string | null> => {
    if (sending.current) return null;
    sending.current = true;
    inFlight.current = true;
    setError(null);
    try {
      const started = await mutateAsync(answers);
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
