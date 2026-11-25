import { useMutation, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/shared/api/errors";
import { postClaim, readMe } from "../api";
import { authKeys } from "../queryKeys";
import type { ClaimChoice } from "../types";

const ALREADY_CLAIMED = "local_already_claimed";

/**
 * Sends the resume choice; the session is opened, `me` is known without re-reading it. A choice
 * replayed (double send, second tab) answers `local_already_claimed` to the person who just
 * resumed the space: if their session is open, `me` is re-read and they enter; otherwise the
 * refusal
 * stays as it is.
 */
export function useClaim() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (choice: ClaimChoice) => {
      try {
        return await postClaim(choice);
      } catch (error) {
        if (error instanceof ApiError && error.code === ALREADY_CLAIMED) {
          const me = await readMe().catch(() => null);
          if (me) return me;
        }
        throw error;
      }
    },
    onSuccess: (me) => {
      queryClient.setQueryData(authKeys.me, me);
    },
  });
}
