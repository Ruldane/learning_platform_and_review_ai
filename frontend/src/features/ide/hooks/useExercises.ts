import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { RunSource } from "@/shared/lib/runSource";
import { createExercise, fetchExercises, generateExercise } from "../api";
import { ideKeys } from "../queryKeys";
import type { ExerciseGenerateIn, ExerciseIn } from "../types";

/** Mes exercices (`GET /ide/exercises`). */
export function useExercises() {
  return useQuery({
    queryKey: ideKeys.exercises,
    queryFn: ({ signal }) => fetchExercises(signal),
  });
}

/** Ajoute un exercice écrit à la main, puis relit la liste. */
export function useCreateExercise() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: ExerciseIn) => createExercise(body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ideKeys.exercises }),
  });
}

/** Fait écrire un exercice par les agents : le résultat porte la session à suivre. */
export function useGenerateExercise() {
  return useMutation({
    mutationFn: ({ body, source }: { body: ExerciseGenerateIn; source?: RunSource }) =>
      generateExercise(body, source),
  });
}
