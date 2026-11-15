import { useEffect, useRef } from "react";

interface Started {
  runId: string;
}

/**
 * Lancer le comité et porter le focus sur la note « le comité délibère » : le bouton que January
 * vient d'activer se grise, le focus ne doit pas s'y perdre. Le focus n'est posé que pour un
 * lancement de January, jamais pour une exécution déjà en cours à l'arrivée.
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
