import { useQuery } from "@tanstack/react-query";
import { readMe } from "../api";
import { authKeys } from "../queryKeys";
import type { Me } from "../types";

/**
 * The signed-in user. A 401 `auth_required` is not a failure: it is
 * `null` (« pas de session »), which avoids a re-read failing in a loop; other errors stay errors.
 * No retry: the gate offers « Réessayer ».
 */
export function useMe() {
  return useQuery<Me | null>({
    queryKey: authKeys.me,
    queryFn: ({ signal }) => readMe(signal),
    retry: false,
  });
}
