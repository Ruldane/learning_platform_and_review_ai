import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { useNavigate } from "react-router";
import { ApiError, errorMessage } from "@/shared/api/errors";
import { studySessionPath } from "@/shared/lib/studyRoutes";
import { startStudy } from "../api";
import { openSessionIn } from "../toView";
import type { StudyStart } from "../types";

/**
 * Start of a session: opens the session, then goes to its page. A session already open (409
 * `study_already_open`, or 200 for the same lesson) is not an error: we go there. 404
 * `no_block_today`: `noBlock`, to offer choosing a lesson (and `onNoBlock`, if it is
 * given). Only one start at a time.
 */
export function useStartStudy(onNoBlock?: () => void) {
  const launch = useLaunchSource();
  const navigate = useNavigate();
  const sending = useRef(false);
  const [error, setError] = useState<string | null>(null);
  const [noBlock, setNoBlock] = useState(false);
  const mutation = useMutation({
    mutationFn: (body: StudyStart) => startStudy(body, launch.source),
  });
  const { mutateAsync } = mutation;

  const start = async (body: StudyStart): Promise<void> => {
    if (sending.current) return;
    sending.current = true;
    setError(null);
    setNoBlock(false);
    try {
      const started = await mutateAsync(body);
      void navigate(studySessionPath(started.study_session_id));
      return; // the page is left: the lock stays set, a second click opens nothing
    } catch (failure) {
      const details = failure instanceof ApiError ? failure.details : null;
      const open =
        failure instanceof ApiError && failure.code === "study_already_open"
          ? openSessionIn(details)
          : null;
      if (open) {
        const kind = (details as { kind?: unknown } | null)?.kind;
        void navigate(studySessionPath(open, kind));
        return;
      }
      if (failure instanceof ApiError && failure.code === "no_block_today") {
        setNoBlock(true);
        onNoBlock?.();
      } else setError(errorMessage(failure));
    }
    sending.current = false;
  };
  return { start, pending: mutation.isPending, error, noBlock, launchMenu: launch.menu };
}
