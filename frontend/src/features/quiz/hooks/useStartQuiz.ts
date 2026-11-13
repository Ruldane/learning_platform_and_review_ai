import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import { startQuiz } from "../api";

/**
 * « Préparer le quiz » d'un module : lance (ou retrouve) le quiz puis ouvre sa page, qui attend la
 * fin de la préparation. Un seul envoi à la fois ; `pendingModuleId` désigne le bouton à couper.
 */
export function useStartQuiz() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const sending = useRef(false);
  const [pendingModuleId, setPending] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const mutation = useMutation({ mutationFn: (moduleId: string) => startQuiz(moduleId) });
  const { mutateAsync } = mutation;

  const prepare = async (moduleId: string): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setPending(moduleId);
    setError(null);
    try {
      const started = await mutateAsync(moduleId);
      void queryClient.invalidateQueries({ queryKey: ["quiz", "list"] });
      void navigate(`/etudier/quiz/${started.quiz_id}`);
      return; // la page se quitte : le verrou reste posé
    } catch (failure) {
      setError(errorMessage(failure));
    }
    sending.current = false;
    setPending(null);
  };
  return { prepare, pendingModuleId, error };
}
