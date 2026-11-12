import type { SessionEvent } from "@/shared/realtime/types";
import type { CouncilStage } from "./components/viewTypes";

/** Tours de débat par défaut après le tour 1 (réglage `debate_rounds`, SPEC 3.1). */
export const DEFAULT_ROUNDS = 3;
/** Plafond de tours du back, tour 1 compris (`council_rules.MAX_ROUNDS`). */
export const MAX_ROUNDS = 8;

export interface CouncilProgress {
  stage: CouncilStage;
  /** Tour en cours du débat (0 : pas encore commencé). */
  round: number;
  /**
   * Tours prévus en tout, tour 1 compris (`1 + debate_rounds`, 8 au plus, D85 §2) ; jamais moins
   * que le tour en cours (un « autre tour » en ajoute un).
   */
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
 * (« autre tour » : retour au débat). `debateRounds` vient des réglages : le back fait le tour 1
 * (positions) puis `debateRounds` tours de débat.
 */
export function councilStage(
  events: SessionEvent[],
  hasProgram: boolean,
  debateRounds: number = DEFAULT_ROUNDS,
): CouncilProgress {
  const planned = Math.min(1 + debateRounds, MAX_ROUNDS);
  let now: CouncilProgress = { stage: "framing", round: 0, rounds: planned };
  for (const event of events) now = advance(now, event);
  return {
    stage: hasProgram ? "program" : now.stage,
    round: now.round,
    rounds: Math.max(planned, now.round),
  };
}
