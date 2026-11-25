import { useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { useLaunchSource } from "@/shared/session-ui";
import type { ExerciseDraft } from "../components/viewTypes";
import { useCreateExercise, useGenerateExercise } from "./useExercises";
import { useCreateSession } from "./useSessions";

/** The files of a hand-written exercise: the starter code and, if any, its tests. */
export function exerciseFiles(draft: ExerciseDraft): Record<string, string> {
  const files: Record<string, string> = { "main.py": draft.starter };
  if (draft.tests.trim() !== "") files["test_main.py"] = draft.tests;
  return files;
}

/**
 * The home page actions: add an exercise, have one generated, open a session
 * (resume it if it exists, otherwise create it), then go to the editor.
 */
export function useHomeActions() {
  const navigate = useNavigate();
  const createExercise = useCreateExercise();
  const generate = useGenerateExercise();
  const provider = useLaunchSource();
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

  /** Opens the session `sessionId`; without it, creates one on `exerciseId` (`null`: free). */
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
      generate.mutate({ body: { topic, level }, source: provider.source });
    },
    launchMenu: provider.menu,
    generated: generate.data ?? null,
    creating: createExercise.isPending,
    generating: generate.isPending,
    opening: createSession.isPending,
    notice,
    formError: formError ? errorMessage(formError) : null,
    openError,
  };
}
