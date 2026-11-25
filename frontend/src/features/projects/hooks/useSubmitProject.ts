import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useRef } from "react";
import { submitProject } from "../api";
import { errorCode, openReviewSession, submitFailure } from "../errors";
import { projectKeys } from "../queryKeys";
import type { ProjectOut, SubmissionView } from "../types";

/** The submission sent: its session, or (409 `review_in_progress`) the running evaluation. */
export interface Submitted {
  sessionId: string | null;
  resumed: boolean;
}

async function send(projectId: string, submission: SubmissionView): Promise<Submitted> {
  try {
    const started = await submitProject(projectId, submission);
    return { sessionId: started.session_id, resumed: false };
  } catch (error) {
    const open = openReviewSession(error);
    if (open !== undefined) return { sessionId: open, resumed: true };
    throw error;
  }
}

/**
 * « Rendre le projet » holds a submission from click until the project is re-read (`reviewing`):
 * a second click (double click, repeated Enter) sends nothing, during the send or while the form
 * is still shown after the project no longer awaits one. A 409 `review_in_progress` is not
 * an error (the open evaluation is followed, `resumed`); a 422 is sorted by field into `refusal`,
 * any other refusal (409 `project_not_ready` or `project_validated`, 413, 503) into `message`.
 */
export function useSubmitProject(projectId: string) {
  const client = useQueryClient();
  const sending = useRef(false);
  const mutation = useMutation({
    mutationFn: (submission: SubmissionView) => send(projectId, submission),
    // Expected: the form stays locked until the `reviewing` status is read.
    onSuccess: async () => {
      await Promise.all([
        client.invalidateQueries({ queryKey: projectKeys.one(projectId) }),
        client.invalidateQueries({ queryKey: projectKeys.github(projectId) }),
      ]);
    },
    onError: (error) => {
      // The project changed under our eyes (validated, brief still missing): the page re-reads.
      const code = errorCode(error);
      if (code === "project_validated" || code === "project_not_ready") {
        void client.invalidateQueries({ queryKey: projectKeys.one(projectId) });
      }
    },
  });
  const { mutateAsync, error, isError } = mutation;
  const failure = useMemo(() => (isError ? submitFailure(error) : null), [isError, error]);
  const submit = (submission: SubmissionView) => {
    const status = client.getQueryData<ProjectOut>(projectKeys.one(projectId))?.status;
    const open = status === undefined || status === "todo" || status === "to_redo";
    if (sending.current || !open) return Promise.resolve(null);
    sending.current = true;
    return mutateAsync(submission)
      .catch(() => null)
      .finally(() => {
        sending.current = false;
      });
  };
  return {
    submit,
    pending: mutation.isPending,
    /** What the server refuses, by field; stable while the error does not change. */
    refusal: failure?.refusal ?? null,
    message: failure?.general ?? null,
    resumed: mutation.data?.resumed ?? false,
    /** A submission went out from this page: the form clears and the tracker takes focus. */
    submitted: mutation.isSuccess,
  };
}
