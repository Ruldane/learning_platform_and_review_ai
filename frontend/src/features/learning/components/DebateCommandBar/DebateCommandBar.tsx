import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { DebateCommand } from "../viewTypes";

interface DebateCommandBarProps {
  /** Aucune commande possible (session terminée, envoi en cours, en attente d'une réponse). */
  disabled: boolean;
  onCommand: (command: DebateCommand) => void;
}

const COMMANDS: DebateCommand[] = ["another_round", "to_proposals", "more_concrete", "shorter"];

/**
 * Commandes permanentes du débat (SPEC 3.2) : relancer un tour, passer aux propositions, demander
 * plus de concret ou plus de concision. La pause et l'arrêt sont dans les contrôles de la session.
 */
export function DebateCommandBar({ disabled, onCommand }: DebateCommandBarProps) {
  return (
    <div role="group" aria-label={t("learning.commands.label")} className="flex flex-wrap gap-2">
      {COMMANDS.map((command) => (
        <Button
          key={command}
          variant="outline"
          size="sm"
          disabled={disabled}
          onClick={() => onCommand(command)}
        >
          {t(`session.commands.${command}`)}
        </Button>
      ))}
    </div>
  );
}
