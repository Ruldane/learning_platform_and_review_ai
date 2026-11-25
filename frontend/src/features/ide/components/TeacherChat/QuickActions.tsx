import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface QuickActionsProps {
  busy: boolean;
  canExplain: boolean;
  onHint: () => void;
  onWhy: () => void;
}

/** Quick requests near the input; when busy, the buttons stay focusable. */
export function QuickActions({ busy, canExplain, onHint, onWhy }: QuickActionsProps) {
  return (
    <div role="group" aria-label={t("ide.chat.quick")} className="flex flex-wrap gap-2">
      <Button
        variant="outline"
        size="sm"
        type="button"
        aria-disabled={busy}
        onClick={busy ? undefined : onHint}
      >
        {t("ide.teacher.hint")}
      </Button>
      <Button
        variant="outline"
        size="sm"
        type="button"
        disabled={!canExplain}
        aria-disabled={busy}
        onClick={busy ? undefined : onWhy}
      >
        {t("ide.teacher.why")}
      </Button>
    </div>
  );
}
