import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import type { RadarRunRequestView } from "../../components/viewTypes";
import type { useStartRadar } from "../../hooks/useStartRadar";

/**
 * « Lancer un relevé » : un lancement tient du clic jusqu'à ce que le relevé à suivre soit lu : un
 * second clic (double clic, Entrée répétée) n'envoie rien, il ne peut donc pas produire un 409 qui
 * écraserait la session du 202. Le lancement mène à `/carriere/radar/:runId` ; la session du 202
 * reste dans `starter.started`.
 */
export function useLaunch(
  starter: ReturnType<typeof useStartRadar>,
  runId: string | null,
  viewedId: string | undefined,
) {
  const navigate = useNavigate();
  const launching = useRef(false);
  useEffect(() => {
    if (runId !== null && viewedId === runId) launching.current = false;
  }, [runId, viewedId]);
  return (request: RadarRunRequestView) => {
    if (launching.current) return;
    launching.current = true;
    void starter.start(request).then((started) => {
      if (!started) {
        launching.current = false;
        return;
      }
      void navigate(`/carriere/radar/${started.runId}`);
    });
  };
}
