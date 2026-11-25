import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { TakeTheirs } from "./TakeTheirs";

interface ConflictCardProps {
  file: string;
  /** Claude's version (the server's): never applied without your choice. */
  theirs: string;
  onKeepMine: () => void;
  onTakeTheirs: () => void;
}

/**
 * Claude changed a file where you had unsaved edits. Your edits stay on
 * the screen; you can read Claude's version, then keep yours or take theirs. Nothing
 * is lost without your action.
 */
export function ConflictCard({ file, theirs, onKeepMine, onTakeTheirs }: ConflictCardProps) {
  const [viewing, setViewing] = useState(false);
  const bodyId = useId();
  return (
    <section
      role="alert"
      aria-label={t("ide.claude.conflictTitle", { file })}
      className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3"
    >
      <p className="text-sm font-medium">{t("ide.claude.conflictTitle", { file })}</p>
      <p className="text-sm">{t("ide.claude.conflictText")}</p>
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          aria-expanded={viewing}
          aria-controls={bodyId}
          onClick={() => setViewing((open) => !open)}
        >
          {viewing ? t("ide.claude.hide") : t("ide.claude.view")}
        </Button>
        <Button onClick={onKeepMine}>{t("ide.claude.keepMine")}</Button>
      </div>
      <p className="text-xs text-muted-foreground">{t("ide.claude.keepMineHint")}</p>
      <div id={bodyId} hidden={!viewing} className="flex flex-col gap-2">
        {viewing ? (
          <>
            <pre
              tabIndex={0}
              aria-label={t("ide.claude.versionLabel", { file })}
              className="max-h-64 overflow-auto rounded-lg bg-muted p-2 font-mono text-sm whitespace-pre-wrap break-words"
            >
              {theirs}
            </pre>
            <TakeTheirs file={file} onConfirm={onTakeTheirs} />
          </>
        ) : null}
      </div>
    </section>
  );
}
