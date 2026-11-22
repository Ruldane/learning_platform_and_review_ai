import type { ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface MarkLearnedActionProps {
  learning: boolean;
  relaunch: boolean;
  launchMenu: ReactNode;
  onClick: () => void;
}

export function MarkLearnedAction({
  learning,
  relaunch,
  launchMenu,
  onClick,
}: MarkLearnedActionProps) {
  return (
    <div className="flex flex-wrap items-end gap-2">
      {learning ? null : launchMenu}
      <Button variant="outline" size="sm" disabled={learning} onClick={onClick}>
        {t(relaunch ? "memory.documents.relaunch" : "memory.documents.markLearned")}
      </Button>
    </div>
  );
}
