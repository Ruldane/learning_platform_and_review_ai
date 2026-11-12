import type { SessionEvent } from "@/shared/realtime/types";
import type { CouncilStage } from "./components/viewTypes";

/** Nombre de tours par défaut (réglage `debate_rounds`, SPEC 3.1). */
export const DEFAULT_ROUNDS = 3;

export interface CouncilProgress {
  stage: CouncilStage;
  /** Tour en cours du débat (0 : pas encore commencé). */
  round: number;
  /** Tours prévus, jamais moins que le tour en cours (un « autre tour » en ajoute un). */
  rounds: number;
}

/** `moderator-tour-2`, `skeptic-tour-3` : le tour est dans l'identifiant du message. */
const TOUR = /-tour-(\d+)$/;
/** Position du tour 1 (`strategist-positions`) et bilan du Modérateur : le débat tourne. */
const DEBATE_MESSAGE = /-(?:positions|bilan-\d+)$/;
/** Le Modérateur annonce le choix : la suite est le programme (`finalize`, D85). */
const CHOICE_MESSAGE = "moderator-choix";

const isWebTool = (tool: string) => tool.startsWith("web_");

/** Étape et tour après `event`. La recherche ne compte qu'avant le débat (un débatteur peut lire le web). */
function advance(now: CouncilProgress, event: SessionEvent): CouncilProgress {
  switch (event.type) {
    case "tool.called":
      return isWebTool(event.payload.tool) && now.stage === "framing"
        ? { ...now, stage: "research" }
        : now;
    case "source.found":
      return now.stage === "framing" ? { ...now, stage: "research" } : now;
    case "agent.message": {
      const id = event.payload.message_id;
      const tour = TOUR.exec(id);
      if (tour) return { ...now, stage: "debate", round: Math.max(now.round, Number(tour[1])) };
      if (DEBATE_MESSAGE.test(id))
        return { ...now, stage: "debate", round: Math.max(now.round, 1) };
      return id === CHOICE_MESSAGE ? { ...now, stage: "program" } : now;
    }
    case "proposal.ready":
      return now.stage === "program" ? now : { ...now, stage: "proposals" };
    case "interrupt.requested":
      return event.payload.kind === "choose_path" && now.stage !== "program"
        ? { ...now, stage: "proposals" }
        : now;
    default:
      return now;
  }
}

/**
 * Étape du Conseil déduite des événements de sa session (SPEC 3.1), sans état à part : cadrage
 * tant que rien d'autre n'est arrivé ; recherche dès un outil `web_*` ou une source ; débat à
 * chaque message « tour-n » (le tour en vient) ; propositions dès `proposal.ready` ou la question
 * du choix ; programme dès le choix annoncé ou un programme connu. Le dernier événement l'emporte
 * (« autre tour » : retour au débat). `plannedRounds` vient des réglages.
 */
export function councilStage(
  events: SessionEvent[],
  hasProgram: boolean,
  plannedRounds: number = DEFAULT_ROUNDS,
): CouncilProgress {
  let now: CouncilProgress = { stage: "framing", round: 0, rounds: plannedRounds };
  for (const event of events) now = advance(now, event);
  return {
    stage: hasProgram ? "program" : now.stage,
    round: now.round,
    rounds: Math.max(plannedRounds, now.round),
  };
}
