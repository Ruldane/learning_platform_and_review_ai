import { useMutation, useQueryClient } from "@tanstack/react-query";
import { startApplicationInterview, startFreeInterview } from "../api";
import { applicationsErrorMessage, errorCode, openInterviewId } from "../errors";
import { applicationsKeys } from "../queryKeys";
import type { InterviewDurationView, InterviewLanguageView, InterviewModeView } from "../types";

/** Les réglages d'un entretien. */
export interface InterviewSettings {
  mode: InterviewModeView;
  durationMin: InterviewDurationView;
  language: InterviewLanguageView;
}

/** Sur quoi porte un entretien sans fiche : une offre, ou un intitulé de poste. */
export type FreeTarget = { postingId: string } | { role: string };

interface Started {
  interviewId: string;
  /** Un entretien était déjà ouvert : on le reprend. */
  resumed: boolean;
}

async function launch(
  applicationId: string | null,
  settings: InterviewSettings,
  target: FreeTarget | null,
): Promise<Started> {
  const body = {
    mode: settings.mode,
    duration_min: settings.durationMin,
    language: settings.language,
  };
  try {
    const started = applicationId
      ? await startApplicationInterview(applicationId, body)
      : await startFreeInterview({
          ...body,
          ...(target && "postingId" in target ? { posting_id: target.postingId } : {}),
          ...(target && "role" in target ? { role: target.role } : {}),
        });
    return { interviewId: started.interview_id, resumed: false };
  } catch (error) {
    const open = openInterviewId(error);
    if (open) return { interviewId: open, resumed: true };
    throw error;
  }
}

/**
 * « Commencer l'entretien » : `start` résout à l'identifiant de l'entretien à suivre. Un 409
 * `interview_in_progress` n'est pas une panne : on reprend l'entretien ouvert (`resumed`).
 */
export function useStartInterview(applicationId: string | null) {
  const client = useQueryClient();
  const mutation = useMutation({
    mutationFn: (args: { settings: InterviewSettings; target: FreeTarget | null }) =>
      launch(applicationId, args.settings, args.target),
    onSuccess: () =>
      client.invalidateQueries({ queryKey: applicationsKeys.interviews(applicationId) }),
  });
  const { mutateAsync } = mutation;
  return {
    start: (settings: InterviewSettings, target: FreeTarget | null = null) =>
      mutateAsync({ settings, target }).then(
        (started) => started,
        () => null,
      ),
    pending: mutation.isPending,
    error: mutation.isError ? applicationsErrorMessage(mutation.error) : null,
    /** Le profil validé manque : January doit le faire avant de commencer. */
    profileMissing: mutation.isError && errorCode(mutation.error) === "profile_required",
  };
}
