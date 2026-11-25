import { useMutation } from "@tanstack/react-query";
import { useNavigate } from "react-router";
import { errorMessage } from "@/shared/api/errors";
import type { RunSource } from "@/shared/lib/runSource";
import { validateGap } from "../api";

/** « Je les maîtrise déjà »: prepares the validation quiz, then opens its page. */
export function useValidateGap(postingId: string, provider?: RunSource) {
  const navigate = useNavigate();
  const mutation = useMutation({
    mutationFn: (skills: string[]) => validateGap(postingId, skills, provider),
    onSuccess: (started) => void navigate(`/study/quiz/${started.quiz_id}`),
  });
  return {
    validate: (skills: string[]) => mutation.mutate(skills),
    pending: mutation.isPending,
    failure: mutation.isError ? errorMessage(mutation.error) : null,
  };
}
