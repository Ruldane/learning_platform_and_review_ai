import { startSession } from "@/shared/realtime/sessionApi";
import type { ResearchBenchInput } from "./components/viewTypes";

/** Graphe du banc d'essai de l'Éclaireur (D77). */
export const RESEARCH_GRAPH = "web_research";

/** `POST /sessions` du parcours `web_research` : une requête et des adresses à lire en plus. */
export function startResearch({ query, urls }: ResearchBenchInput): Promise<string> {
  return startSession(RESEARCH_GRAPH, { query, urls });
}
