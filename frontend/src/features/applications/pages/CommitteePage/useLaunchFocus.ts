import { useEffect, useRef } from "react";

interface Started {
  runId: string;
}

/**
 * Starts the committee and moves focus to the « le comité délibère » note: the button January
 * just activated greys out, focus must not be lost there. Focus is set only for a
 * launch by January, never for a run already in progress on arrival.
 */
export function useLaunchFocus(
  running: boolean,
  runId: string | null,
  start: (versionId: string) => Promise<Started | null>,
  follow: (runId: string) => void,
) {
  const note = useRef<HTMLParagraphElement>(null);
  const wanted = useRef(false);

  useEffect(() => {
    if (running && wanted.current) {
      wanted.current = false;
      note.current?.focus();
    }
  }, [running, runId]);

  async function launch(versionId: string) {
    wanted.current = true;
    const started = await start(versionId);
    if (started) follow(started.runId);
    else wanted.current = false;
  }

  return { note, launch };
}
