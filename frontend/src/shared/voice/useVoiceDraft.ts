import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { errorMessage } from "@/shared/api/errors";
import { transcribe } from "./api";
import { openCapture, type VoiceCapture } from "./capture";
import { RECORDING_SECONDS } from "./wav";

type Stage = "idle" | "permission" | "recording" | "ready" | "transcribing";
interface View {
  stage: Stage;
  hasSamples?: boolean;
  notice?: string;
  error?: string;
}

interface Attempt {
  controller: AbortController;
  capture?: VoiceCapture;
  timer?: number;
  clip?: Blob;
}

function clearAttempt(attempt?: Attempt | null) {
  if (!attempt) return;
  window.clearTimeout(attempt.timer);
  attempt.controller.abort();
  attempt.capture?.cancel();
  attempt.clip = undefined;
}

function useAttempts() {
  const active = useRef<Attempt | null>(null);
  const [view, setView] = useState<View>({ stage: "idle" });
  useEffect(
    () => () => {
      const previous = active.current;
      active.current = null;
      clearAttempt(previous);
    },
    [],
  );
  const reset = (next: View = { stage: "idle" }) => {
    clearAttempt(active.current);
    active.current = null;
    setView(next);
  };
  const takeClip = () => {
    const attempt = active.current;
    if (!attempt?.clip) return null;
    const clip = attempt.clip;
    attempt.clip = undefined;
    return { attempt, clip };
  };
  return { active, view, setView, reset, takeClip };
}

function useRecording({ active, setView, reset }: ReturnType<typeof useAttempts>) {
  const finish = () => {
    const attempt = active.current;
    if (!attempt?.capture) return;
    window.clearTimeout(attempt.timer);
    attempt.clip = attempt.capture.finish() ?? undefined;
    attempt.capture = undefined;
    if (attempt.clip) setView({ stage: "ready" });
    else reset({ stage: "idle", error: t("voice.noAudio") });
  };
  const start = async () => {
    if (active.current) return;
    const attempt: Attempt = { controller: new AbortController() };
    active.current = attempt;
    setView({ stage: "permission" });
    let heard = false;
    try {
      attempt.capture = await openCapture(
        attempt.controller.signal,
        () => {
          heard = true;
          if (active.current === attempt && attempt.capture) {
            setView({ stage: "recording", hasSamples: true });
          }
        },
        () => {
          if (active.current === attempt) finish();
        },
      );
      if (active.current !== attempt) {
        attempt.capture.cancel();
        return;
      }
      attempt.timer = window.setTimeout(finish, RECORDING_SECONDS * 1000);
      setView({ stage: "recording", hasSamples: heard });
    } catch {
      if (active.current === attempt) reset({ stage: "idle", error: t("voice.microphoneError") });
    }
  };
  return { start, finish };
}

export function useVoiceDraft(onDraft: (text: string) => void) {
  const attempts = useAttempts();
  const { active, view, setView, reset } = attempts;
  const recording = useRecording(attempts);
  const send = async () => {
    const ready = attempts.takeClip();
    if (!ready) return;
    const { attempt, clip } = ready;
    setView({ stage: "transcribing" });
    try {
      const caption = await transcribe(clip, attempt.controller.signal);
      if (active.current === attempt) {
        onDraft(caption);
        reset({ stage: "idle", notice: t("voice.review") });
      }
    } catch (error) {
      if (active.current === attempt) {
        reset({ stage: "idle", error: errorMessage(error) });
      }
    }
  };
  return {
    view,
    ...recording,
    send,
    cancel: () => reset({ stage: "idle", notice: t("voice.cancelled") }),
  };
}
