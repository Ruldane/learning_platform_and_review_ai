import { ReplanForm } from "../../components/ReplanForm";
import { useStartReplan } from "../../hooks/useStartReplan";

interface ReplanStartProps {
  programId: string;
  onSession: (sessionId: string) => void;
}

/** The start: the form launches the replan; a replan already open is followed. */
export function ReplanStart({ programId, onSession }: ReplanStartProps) {
  const replan = useStartReplan(programId, onSession);
  return (
    <ReplanForm
      launchMenu={replan.launchMenu}
      busy={replan.pending}
      error={replan.error}
      onSubmit={({ availableMinutes, message }) =>
        void replan.start({ available_minutes: availableMinutes, message })
      }
    />
  );
}
