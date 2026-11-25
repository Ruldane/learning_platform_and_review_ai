import { useQuery } from "@tanstack/react-query";
import { fetchProfile, fetchProfileVersions } from "../api";
import { cvKeys } from "../queryKeys";

export const POLL_MS = 3000;

/**
 * `GET /profile`. While a document reading is running (`session_id`), the profile is reloaded
 * every `pollMs`: the session stream does most of the work, this reload catches up.
 */
export function useProfile(pollMs = POLL_MS) {
  return useQuery({
    queryKey: cvKeys.profile,
    queryFn: ({ signal }) => fetchProfile(signal),
    refetchInterval: (state) => (state.state.data?.session_id ? pollMs : false),
  });
}

/** `GET /profile/versions`: the history of the master profile. */
export function useProfileVersions() {
  return useQuery({
    queryKey: cvKeys.profileVersions,
    queryFn: ({ signal }) => fetchProfileVersions(signal),
  });
}
