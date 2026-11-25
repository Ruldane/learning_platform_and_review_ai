import { useState, type FormEvent } from "react";
import { usePostingChoices } from "../../hooks/usePostingChoices";
import { useStartInterview, type InterviewSettings } from "../../hooks/useStartInterview";
import { EMPTY_TARGET, toTarget } from "./targetDraft";

const DEFAULTS: InterviewSettings = { mode: "mixed", durationMin: 30, language: "en" };

/**
 * The settings form state and its submission. Without a record (`applicationId` null), the target
 * (posting or title) is required: nothing is sent without it, and the form says so.
 */
export function useInterviewSetup(
  applicationId: string | null,
  onStarted: (interviewId: string, resumed: boolean) => void,
) {
  const free = applicationId === null;
  const [settings, setSettings] = useState(DEFAULTS);
  const [target, setTarget] = useState(EMPTY_TARGET);
  const [missing, setMissing] = useState(false);
  const postings = usePostingChoices(free).data ?? [];
  const launcher = useStartInterview(applicationId);

  async function submit(event: FormEvent) {
    event.preventDefault();
    const chosen = free ? toTarget(target, postings.length > 0) : null;
    setMissing(free && chosen === null);
    if (free && chosen === null) return;
    const started = await launcher.start(settings, chosen);
    if (started) onStarted(started.interviewId, started.resumed);
  }

  return { free, settings, setSettings, target, setTarget, missing, postings, launcher, submit };
}
