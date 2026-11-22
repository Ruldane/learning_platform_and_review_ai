import { useEffect, useRef, useState } from "react";
import { errorMessage } from "@/shared/api/errors";
import { speak } from "../api";

type Clip = { source: string; url?: string; error?: string; loading?: boolean };
type Attempt = { controller: AbortController; url?: string };

function dispose(attempt: Attempt | null) {
  attempt?.controller.abort();
  if (attempt?.url) URL.revokeObjectURL(attempt.url);
}

export function usePlayback(source: string) {
  const active = useRef<Attempt | null>(null);
  const [clip, setClip] = useState<Clip | null>(null);
  const clear = () => {
    dispose(active.current);
    active.current = null;
  };
  useEffect(
    () => () => {
      dispose(active.current);
      active.current = null;
    },
    [source],
  );
  const cancel = () => {
    clear();
    setClip(null);
  };
  const prepare = async (text: string) => {
    clear();
    const attempt: Attempt = { controller: new AbortController() };
    active.current = attempt;
    setClip({ source, loading: true });
    try {
      const audio = await speak(text, attempt.controller.signal);
      if (active.current === attempt) {
        attempt.url = URL.createObjectURL(audio);
        setClip({ source, url: attempt.url });
      }
    } catch (error) {
      if (active.current === attempt) setClip({ source, error: errorMessage(error) });
    }
  };
  return { prepare, cancel, view: clip?.source === source ? clip : null };
}
