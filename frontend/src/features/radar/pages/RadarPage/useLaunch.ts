import { useEffect, useRef } from "react";
import { useNavigate } from "react-router";
import type { RadarRunRequestView } from "../../components/viewTypes";
import type { useStartRadar } from "../../hooks/useStartRadar";

/**
 * « Lancer un relevé »: a launch holds from the click until the sweep to follow is read: a
 * second click (double click, repeated Enter) sends nothing, so it cannot produce a 409 that
 * would overwrite the 202 session. The launch leads to `/career/radar/:runId`; the 202 session
 * stays in `starter.started`.
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
      void navigate(`/career/radar/${started.runId}`);
    });
  };
}
