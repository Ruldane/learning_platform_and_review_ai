import { ReplanForm } from "../../components/ReplanForm";
import { useStartReplan } from "../../hooks/useStartReplan";

interface ReplanStartProps {
  programId: string;
  onSession: (sessionId: string) => void;
}

/** Le départ : le formulaire lance la replanification ; une replanification déjà ouverte est suivie. */
export function ReplanStart({ programId, onSession }: ReplanStartProps) {
  const replan = useStartReplan(programId, onSession);
  return (
    <ReplanForm
      busy={replan.pending}
      error={replan.error}
      onSubmit={({ availableMinutes, message }) =>
        void replan.start({ available_minutes: availableMinutes, message })
      }
    />
  );
}
