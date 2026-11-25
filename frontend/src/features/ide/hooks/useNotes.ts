import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { acceptNote, fetchNotes, rejectNote } from "../api";
import { ideKeys } from "../queryKeys";
import { liveOptions } from "./live";

/** The session's notes (`GET /ide/sessions/{id}/notes`), re-read live. */
export function useNotes(sessionId: string) {
  return useQuery({
    queryKey: ideKeys.notes(sessionId),
    queryFn: ({ signal }) => fetchNotes(sessionId, signal),
    ...liveOptions,
  });
}

/**
 * Accepting applies the proposal **on the server side**: we take the session it returns and do not
 * recompute the file. Notes are re-read in every case (a 409 `note_stale` makes them
 * switch to « périmée »).
 */
export function useAcceptNote(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => acceptNote(noteId),
    onSuccess: (session) => queryClient.setQueryData(ideKeys.session(sessionId), session),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ideKeys.notes(sessionId) }),
  });
}

/** Rejects a proposal. */
export function useRejectNote(sessionId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (noteId: string) => rejectNote(noteId),
    onSettled: () => queryClient.invalidateQueries({ queryKey: ideKeys.notes(sessionId) }),
  });
}
