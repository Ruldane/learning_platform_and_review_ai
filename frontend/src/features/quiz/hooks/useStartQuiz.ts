import type { RunSource } from "@/shared/lib/runSource";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { startQuiz } from "../api";

/**
 * « Préparer le quiz » for a module: starts (or finds) the quiz, then opens its page, which
 * waits for it to end. One send at a time; `pendingModuleId` names the button to turn off.
 */
export function useStartQuiz() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sending = useRef(false);
  const [pendingModuleId, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: ({ moduleId, source }: { moduleId: string; source?: RunSource }) => startQuiz(moduleId, source),
  });
  const { mutateAsync } = mutation;

  const prepare = async (moduleId: string, source?: RunSource): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setPending(moduleId);
    setError(null);
    try {
      const started = await mutateAsync({ moduleId, source });
      void queryClient.invalidateQueries({ queryKey: ["quiz", "list"] });
      void navigate(`/study/quiz/${started.quiz_id}`);
      return; // the page is leaving: the lock stays in place
    } catch (failure) {
      setError(errorMessage(failure));
    }
    sending.current = false;
    setPending(null);
  };
  return { prepare, pendingModuleId, error };
}
