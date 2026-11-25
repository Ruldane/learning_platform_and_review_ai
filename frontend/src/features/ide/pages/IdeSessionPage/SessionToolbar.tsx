import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";

interface SessionToolbarProps {
  running: boolean;
  dirty: boolean;
  saving: boolean;
  saveError: string | null;
  runError: string | null;
  onRun: () => void;
  onCheck: () => void;
}

function saveState(dirty: boolean, saving: boolean): string {
  if (saving) return t("ide.toolbar.saving");
  return dirty ? t("ide.toolbar.unsaved") : t("ide.toolbar.saved");
}

/** Run, check, and the save state in full words. */
export function SessionToolbar(props: SessionToolbarProps) {
  const { running, dirty, saving, saveError, runError, onRun, onCheck } = props;
  return (
    <div className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center gap-2">
        <Button
          aria-disabled={running}
          aria-label={t("ide.toolbar.runLabel")}
          onClick={running ? undefined : onRun}
        >
          {t("ide.toolbar.run")}
        </Button>
        <Button variant="outline" aria-disabled={running} onClick={running ? undefined : onCheck}>
          {t("ide.toolbar.check")}
        </Button>
        <p role="status" className="text-sm text-muted-foreground">
          {saveState(dirty, saving)}
        </p>
      </div>
      <p className="text-xs text-muted-foreground">
        {t("ide.editor.runHint")} {t("ide.editor.tabHint")}
      </p>
      {saveError ? (
        <InlineError message={t("ide.toolbar.saveFailed", { message: saveError })} />
      ) : null}
      {runError ? <InlineError message={runError} /> : null}
    </div>
  );
}
