/** View types of the Council components: independent of the API contract (D34). */

/** The five Council stages (SPEC 3.1): framing leads to the program. */
export type CouncilStage = "framing" | "research" | "debate" | "proposals" | "program";

/** Debate command: a message with no text that the agents read in the next round (D82). */
export type DebateCommand = "another_round" | "to_proposals" | "more_concrete" | "shorter";

/** A path proposed by the Council (SPEC 3.2). */
export interface ProposalView {
  id: string;
  /** 1 for the first proposal, 2 for the next… */
  rank: number;
  name: string;
  promise: string;
  durationWeeks: number;
  /** Weekly load, in hours (can be fractional: 7.5). */
  weeklyHours: number;
  skills: string[];
  finalProject: string;
  tradeoffs: string[];
  /** « comparaison » table where the proposal is drawn; `null` if there is none. */
  boardId: string | null;
  /** The path January chose (only one per batch). */
  chosen: boolean;
}

/** The tabbed areas of the Council page. */
export type CouncilTab = "board" | "sources" | "proposals";

/** What January enters for a goal (SPEC 3.1, step 1); empty optional fields are `null`. */
export interface GoalInput {
  text: string;
  targetRole: string | null;
  /** Deadline, in `YYYY-MM-DD` format. */
  deadline: string | null;
  /** Hours per week, from 1 to 40. */
  weeklyHours: number | null;
}

/** Goal status: the Council deliberates, a path is chosen, a program is scheduled. */
export type GoalStatusView = "council" | "chosen" | "planned";

/** One row of the goals list. */
export interface GoalRow {
  id: string;
  text: string;
  targetRole: string | null;
  deadline: string | null;
  weeklyHours: number | null;
  status: GoalStatusView;
  /** The goal's program, if it exists: its link. */
  programId: string | null;
}
