import type { RunSource } from "@/shared/lib/runSource";
import { startSession } from "@/shared/realtime/sessionApi";
import type { ResearchBenchInput } from "./components/viewTypes";

/** The graph of the Scout's test bench (D77). */
export const RESEARCH_GRAPH = "web_research";

/** `POST /sessions` of the `web_research` path: a query and addresses to read in addition. */
export function startResearch({ query, urls }: ResearchBenchInput, source?: RunSource): Promise<string> {
  return startSession(RESEARCH_GRAPH, { query, urls }, source);
}
