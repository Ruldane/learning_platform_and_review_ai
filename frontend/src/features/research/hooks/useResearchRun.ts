import { useLaunchSource } from "@/shared/session-ui";
import { useMutation } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import type { SocketFactory } from "@/shared/realtime/socket";
import { useSessionStream } from "@/shared/realtime/useSessionStream";
import { startResearch } from "../api";
import type { ResearchBenchInput } from "../components/viewTypes";

export const SESSION_PARAM = "session";

/**
 * The current test. Its identifier lives in the URL (`?session=<id>`): a reload rejoins the
 * session (the stream replays the events from the start). `createSocket` serves only the tests.
 */
export function useResearchRun(createSocket?: SocketFactory) {
  const launch = useLaunchSource();
  const [params, setParams] = useSearchParams();
  const sessionId = params.get(SESSION_PARAM);
  const stream = useSessionStream(sessionId, { createSocket });
  const start = useMutation({
    mutationFn: (input: ResearchBenchInput) => startResearch(input, launch.source),
    onSuccess: (id) => setParams({ [SESSION_PARAM]: id }),
  });
  const restart = () => setParams({});

  return { sessionId, stream, start, restart, launchMenu: launch.menu };
}
