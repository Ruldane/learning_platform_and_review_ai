import { useIsFetching, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { regenerateDrafts } from "../api";
import { t } from "@/shared/i18n/t";
import { errorCode, openReviewSession, readableMessage } from "../errors";
import { projectKeys } from "../queryKeys";

/** The session writing the drafts, or (409 `review_in_progress`) the one already running. */
interface Regenerating {
  sessionId: string;
}

async function send(projectId: string): Promise<Regenerating> {
  try {
    return { sessionId: (await regenerateDrafts(projectId)).session_id };
  } catch (error) {
    // A write already running can be followed; without its id (the server is not bound to send it),
    // there is nothing to follow: the error then says to come back in a moment.
    const open = openReviewSession(error);
    if (typeof open === "string") return { sessionId: open };
    throw error;
  }
}

/**
 * The refusal text for THIS button (the texts in `errors.ts` refer to the submission evaluation).
 */
function readable(error: unknown): string {
  const code = errorCode(error);
  if (code === "review_in_progress") return t("projects.page.draftsInProgress");
  if (code === "project_not_validated") return t("projects.page.draftsNotValidated");
  return readableMessage(error);
}

/**
 * « Régénérer les brouillons » (`POST /projects/{id}/drafts`, 202): a validated project with none;
 * one click holds until the response (a double click sends nothing more). 409
 * `drafts_present` or `project_not_validated`: the project changed; the page re-reads.
 * `sessionId` is the session to follow, until the page has received another one.
 */
export function useRegenerateDrafts(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const rereading = useIsFetching({ queryKey: projectKeys.one(projectId) }) > 0;
  const reread = () => client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
  const mutation = useMutation({
    mutationFn: () => send(projectId),
    onSuccess: reread,
    onError: (error) => {
      const code = errorCode(error);
      if (code === "drafts_present" || code === "project_not_validated") void reread();
    },
  });
  const { mutateAsync } = mutation;
  return {
    regenerate: () => {
      if (sending.current) return;
      sending.current = true;
      void mutateAsync()
        .catch(() => null)
        .finally(() => {
          sending.current = false;
        });
    },
    pending: mutation.isPending,
    sessionId: mutation.data?.sessionId ?? null,
    /** The project re-reads: a write result may be about to arrive. */
    rereading,
    error: mutation.isError ? readable(mutation.error) : null,
  };
}

export type DraftsRegeneration = ReturnType<typeof useRegenerateDrafts>;
