import { useEffect, useRef } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { InterviewView } from "../../types";
import { InterviewResult } from "./InterviewResult";

interface InterviewOutcomeProps {
  interview: InterviewView;
  /** Le libellé du retour : « Commencer un autre entretien » après un entretien suivi, « Retour aux réglages » pour un passé. */
  closeLabel: string;
  onClose: () => void;
}

/**
 * Un entretien fini (ou passé) : le titre reçoit le focus à l'arrivée, puis le résultat selon l'état :
 * débrief, réponses sans débrief, arrêt avant toute réponse, ou échec de la session.
 */
export function InterviewOutcome({ interview, closeLabel, onClose }: InterviewOutcomeProps) {
  const title = useRef<HTMLHeadingElement>(null);
  useEffect(() => title.current?.focus(), []);
  return (
    <section className="flex flex-col gap-4">
      <h2 ref={title} tabIndex={-1} className="text-xl font-semibold outline-none">
        {t("applications.debrief.title")}
      </h2>
      <InterviewResult interview={interview} />
      <div>
        <Button type="button" variant="outline" onClick={onClose}>
          {closeLabel}
        </Button>
      </div>
    </section>
  );
}
