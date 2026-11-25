import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { DebateCommand } from "../viewTypes";

interface DebateCommandBarProps {
  /** No command possible (session ended, send in progress, waiting for a response). */
  disabled: boolean;
  onCommand: (command: DebateCommand) => void;
}

const COMMANDS: DebateCommand[] = ["another_round", "to_proposals", "more_concrete", "shorter"];

/**
 * Standing debate commands (SPEC 3.2): rerun a round, move to proposals, ask for
 * more concrete or more concise. Pause and stop are in the session controls.
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
