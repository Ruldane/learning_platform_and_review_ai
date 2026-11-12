import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { startResearch } from "../api";
import type { ResearchBenchInput } from "../components/viewTypes";

export const SESSION_PARAM = "session";

/**
 * L'essai courant. Son identifiant vit dans l'URL (`?session=<id>`) : recharger la page rejoint la
 * session (le flux rejoue les événements depuis le début). `createSocket` ne sert qu'aux tests.
 */
export function useResearchRun(createSocket?: SocketFactory) {
  const [params, setParams] = useSearchParams();
  const sessionId = params.get(SESSION_PARAM);
  const stream = useSessionStream(sessionId, { createSocket });
  const start = useMutation({
    mutationFn: (input: ResearchBenchInput) => startResearch(input),
    onSuccess: (id) => setParams({ [SESSION_PARAM]: id }),
  });
  const restart = () => setParams({});

  return { sessionId, stream, start, restart };
}
