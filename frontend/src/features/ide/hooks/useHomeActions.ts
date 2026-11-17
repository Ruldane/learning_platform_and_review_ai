import { useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import type { ExerciseDraft } from "../components/viewTypes";
import { useCreateExercise, useGenerateExercise } from "./useExercises";
import { useCreateSession } from "./useSessions";

/** Les fichiers d'un exercice écrit à la main : le code de départ et, s'il y en a, ses tests. */
export function exerciseFiles(draft: ExerciseDraft): Record<string, string> {
  const files: Record<string, string> = { "main.py": draft.starter };
  if (draft.tests.trim() !== "") files["test_main.py"] = draft.tests;
  return files;
}

/**
 * Les gestes de la page d'accueil : ajouter un exercice, en faire générer un, ouvrir une séance
 * (la reprendre si elle existe, sinon la créer) puis aller dans l'éditeur.
 */
export function useHomeActions() {
  const navigate = useNavigate();
  const createExercise = useCreateExercise();
  const generate = useGenerateExercise();
  const createSession = useCreateSession();
  const [notice, setNotice] = useState<string | null>(null);
  const [openError, setOpenError] = useState<string | null>(null);

  async function create(draft: ExerciseDraft): Promise<boolean> {
    setNotice(null);
    try {
      await createExercise.mutateAsync({
        title: draft.title.trim(),
        statement: draft.statement.trim(),
        files: exerciseFiles(draft),
        entry: "main.py",
      });
      setNotice(t("ide.form.created"));
      return true;
    } catch {
      return false;
    }
  }

  /** Ouvre la séance `sessionId` ; sans elle, en crée une sur `exerciseId` (`null` : libre). */
  async function open(exerciseId: string | null, sessionId: string | null) {
    setOpenError(null);
    try {
      const id = sessionId ?? (await createSession.mutateAsync(exerciseId)).id;
      void navigate(`/code/${id}`);
    } catch (failure) {
      setOpenError(errorMessage(failure));
    }
  }

  const formError = createExercise.error ?? generate.error;
  return {
    create,
    open,
    generate: (topic: string, level: "beginner" | "intermediate" | "advanced") => {
      setNotice(null);
      generate.mutate({ topic, level });
    },
    generated: generate.data ?? null,
    creating: createExercise.isPending,
    generating: generate.isPending,
    opening: createSession.isPending,
    notice,
    formError: formError ? errorMessage(formError) : null,
    openError,
  };
}
