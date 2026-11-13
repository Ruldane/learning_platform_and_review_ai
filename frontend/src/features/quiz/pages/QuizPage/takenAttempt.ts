import type { AnswerDraft, QuestionView } from "../../components/viewTypes";

/** Un essai envoyé : les questions telles qu'elles s'affichaient, et les réponses (pour les renvoyer). */
export interface TakenAttempt {
  attemptId: string;
  questions: QuestionView[];
  /** `null` quand l'essai est une correction reprise après un rechargement de la page. */
  drafts: AnswerDraft[] | null;
}
