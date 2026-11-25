import type { QueryClient } from "@tanstack/react-query";
import { resetLocalState } from "./localReset";

/** The session queries (`me`): they survive forgetting an account. */
const SESSION_SCOPE = "auth";

/**
 * Forgets everything the previous account had read: the queries (except session ones) and
 * what features keep outside the cache (`resetLocalState`). Used on sign-out, on 401,
 * after « Tout supprimer », and when the account changes in another tab.
 */
export function forgetAccount(queryClient: QueryClient): void {
  queryClient.removeQueries({ predicate: (query) => query.queryKey[0] !== SESSION_SCOPE });
  resetLocalState();
}
