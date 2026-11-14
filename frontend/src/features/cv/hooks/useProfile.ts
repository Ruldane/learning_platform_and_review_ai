import { useQuery } from "@tanstack/react-query";
import { fetchProfile, fetchProfileVersions } from "../api";
import { cvKeys } from "../queryKeys";

export const POLL_MS = 3000;

/**
 * `GET /profile`. Tant qu'une lecture de documents est en cours (`session_id`), le profil est relu
 * toutes les `pollMs` : le flux de la session fait le gros du travail, cette relecture le rattrape.
 */
export function useProfile(pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.profile,
    queryFn: ({ signal }) => fetchProfile(signal),
    refetchInterval: (state) => (state.state.data?.session_id ? pollMs : false),
  });
}

/** `GET /profile/versions` : l'historique du profil maître. */
export function useProfileVersions() {
  return useQuery({
    queryKey: cvKeys.profileVersions,
    queryFn: ({ signal }) => fetchProfileVersions(signal),
  });
}
