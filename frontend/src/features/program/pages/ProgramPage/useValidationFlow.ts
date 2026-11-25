import { useProgramSession } from "../../hooks/useProgramSession";
import { useReviseProgram } from "../../hooks/useReviseProgram";
import { useValidateProgram } from "../../hooks/useValidateProgram";
import type { ProgramOut } from "../../types";

export interface ValidationFlow {
  /** `ready`: waiting for January; `working`: the Strategist revises or validates; `validated`. */
  phase: "ready" | "working" | "validated";
  /** The session waits for validation: a revision may be requested. */
  canRevise: boolean;
  sessionFailed: boolean;
  busy: boolean;
  notice: string | null;
  error: string | null;
  onValidate: () => Promise<void>;
  onRevise: (note: string) => Promise<boolean>;
}

/**
 * The draft's breakpoint no. 3: the Strategist session's state (re-read while it
 * runs), validation through the dedicated route, and revision by resuming the question.
 */
export function useValidationFlow(program: ProgramOut): ValidationFlow {
  const session = useProgramSession(program.session_id, program.status === "draft", program.id);
  const validation = useValidateProgram(program.id);
  const revision = useReviseProgram(program.id);
  const status = session.data?.status;
  const interrupt = session.data?.pending_interrupt ?? null;
  const canRevise = status === "waiting_user" && interrupt?.kind === "validate_program";
  const validated = program.status === "validated" || validation.validated;
  const sessionId = program.session_id;

  return {
    phase: validated ? "validated" : status === "running" ? "working" : "ready",
    canRevise,
    sessionFailed: status === "failed",
    busy: validation.pending || revision.pending,
    notice: validation.notice ?? revision.notice,
    error: validation.error ?? revision.error,
    onValidate: validation.validate,
    onRevise: async (note) =>
      sessionId !== null && interrupt !== null
        ? revision.revise({ sessionId, interruptId: interrupt.interrupt_id, note })
        : false,
  };
}
