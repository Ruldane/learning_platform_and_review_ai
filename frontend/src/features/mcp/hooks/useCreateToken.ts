import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createToken } from "../api";
import { mcpKeys } from "../queryKeys";

/**
 * Crée un jeton. Sa valeur ne vit que dans le résultat de la mutation (en mémoire, jamais dans le
 * cache des lectures ni dans le stockage du navigateur) : `reset` l'oublie une fois copiée.
 */
export function useCreateToken() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: createToken,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: mcpKeys.tokens }),
  });
}
