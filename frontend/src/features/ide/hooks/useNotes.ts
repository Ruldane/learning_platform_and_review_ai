import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { acceptNote, fetchNotes, rejectNote } from "../api";
import { ideKeys } from "../queryKeys";

/** Les notes de la séance (`GET /ide/sessions/{id}/notes`). */
export function useNotes(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.notes(sessionId),
    queryFn: ({ signal }) => fetchNotes(sessionId, signal),
  });
}

/**
 * Accepter applique la proposition **côté serveur** : on prend la séance qu'il rend, on ne
 * recalcule jamais le fichier. Les notes sont relues dans tous les cas (un 409 `note_stale` les
 * fait passer en « périmée »).
 */
export function useAcceptNote(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => acceptNote(noteId),
    onSuccess: (session) => queryClient.setQueryData(ideKeys.session(sessionId), session),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ideKeys.notes(sessionId) }),
  });
}

/** Refuse une proposition. */
export function useRejectNote(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => rejectNote(noteId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ideKeys.notes(sessionId) }),
  });
}
