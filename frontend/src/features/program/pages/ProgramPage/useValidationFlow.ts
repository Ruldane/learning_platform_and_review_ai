import { useProgramSession } from "../../hooks/useProgramSession";
import { useReviseProgram } from "../../hooks/useReviseProgram";
import { useValidateProgram } from "../../hooks/useValidateProgram";
import type { ProgramOut } from "../../types";

export interface ValidationFlow {
  /** `ready` : en attente de January ; `working` : le Stratège révise ou valide ; `validated`. */
  phase: "ready" | "working" | "validated";
  /** La session attend la validation : une révision peut être demandée. */
  canRevise: boolean;
  sessionFailed: boolean;
  busy: boolean;
  notice: string | null;
  error: string | null;
  onValidate: () => Promise<void>;
  onRevise: (note: string) => Promise<boolean>;
}

/**
 * Le point d'arrêt n° 3 d'un brouillon : l'état de la session du Stratège (relue tant qu'elle
 * tourne), la validation par la route dédiée et la révision par la reprise de la question.
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
