import { useLocation, useSearchParams } from "react-router";
import { clampQuestion } from "../../toView";

export interface ChosenLesson {
  lessonId: string;
  /** Le passage de la leçon sur lequel January demande au tuteur (déjà coupé à 2 000 caractères). */
  question: string | null;
}

/** Ce que porte l'état de navigation (« Demander au tuteur ») : tout autre contenu est ignoré. */
function readState(state: unknown): { lessonId: string | null; question: string | null } {
  const record =
    typeof state === "object" && state !== null ? (state as Record<string, unknown>) : {};
  const lessonId =
    typeof record.lessonId === "string" && record.lessonId !== "" ? record.lessonId : null;
  const text = typeof record.question === "string" ? clampQuestion(record.question) : "";
  return { lessonId, question: text === "" ? null : text };
}

/**
 * La leçon choisie hors du bloc du jour : l'état de navigation `{ lessonId, question }` (bouton
 * « Demander au tuteur » d'une leçon) ou `?lecon={id}` (sans question). `null` : le bloc du jour.
 */
export function useChosenLesson(): ChosenLesson | null {
  const location = useLocation();
  const [params] = useSearchParams();
  const fromState = readState(location.state);
  const lessonId = fromState.lessonId ?? params.get("lecon");
  if (lessonId === null || lessonId === "") return null;
  return { lessonId, question: fromState.lessonId === null ? null : fromState.question };
}
