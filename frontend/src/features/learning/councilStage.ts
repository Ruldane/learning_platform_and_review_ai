import type { SessionEvent } from "@/shared/realtime/types";
import type { CouncilStage } from "./components/viewTypes";

/** Default debate rounds after round 1 (`debate_rounds` setting, SPEC 3.1). */
export const DEFAULT_ROUNDS = 3;
/** Backend round cap, round 1 included (`council_rules.MAX_ROUNDS`). */
export const MAX_ROUNDS = 8;

export interface CouncilProgress {
  stage: CouncilStage;
  /** Current debate round (0: not started yet). */
  round: number;
  /**
   * Total planned rounds, round 1 included (`1 + debate_rounds`, 8 at most, D85 §2); never fewer
   * than the current round (an « autre tour » adds one).
   */
  rounds: number;
}

/** `moderator-tour-2`, `skeptic-tour-3`: the round is in the message id. */
const TOUR = /-tour-(\d+)$/;
/** Round 1 positions (`strategist-positions`) and the Moderator's summary: debate is running. */
const DEBATE_MESSAGE = /-(?:positions|bilan-\d+)$/;
/** The Moderator announces the choice: next comes the program (`finalize`, D85). */
const CHOICE_MESSAGE = "moderator-choix";

const isWebTool = (tool: string) => tool.startsWith("web_");

/** Stage and round after `event`. Research counts only before the debate (debaters use the web). */
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
 * Council stage derived from its session events (SPEC 3.1), with no separate state: framing
 * until something else arrives; research as soon as a `web_*` tool or a source; debate at
 * each « tour-n » message (the round comes from it); proposals on `proposal.ready` or the question
 * of the choice; program as soon as the choice is announced or a known program. The last event wins
 * (« autre tour »: back to debate). `debateRounds` comes from settings; the backend runs round 1
 * (positions) then `debateRounds` debate rounds.
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
