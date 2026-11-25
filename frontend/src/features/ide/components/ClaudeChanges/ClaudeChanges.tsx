import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ConflictCard } from "./ConflictCard";

interface ClaudeChangesProps {
  /** The file open in the editor. */
  file: string;
  /** Files Claude changed that the editor loaded as they are. */
  notices: string[];
  /** Files both Claude and you changed: name -> Claude's version. */
  conflicts: Record<string, string>;
  onDismiss: (file: string) => void;
  onKeepMine: (file: string) => void;
  onTakeTheirs: (file: string) => void;
}

/**
 * What Claude did to the files during the session: a message for the open file it
 * changed (the editor shows its version), and a choice card for each conflicting file.
 */
export function ClaudeChanges(props: ClaudeChangesProps) {
  const { file, notices, conflicts, onDismiss, onKeepMine, onTakeTheirs } = props;
  const names = Object.keys(conflicts);
  if (!notices.includes(file) && names.length === 0) return null;
  return (
    <div className="flex flex-col gap-2">
      {notices.includes(file) ? (
        <div className="flex flex-wrap items-center gap-2 rounded-xl border border-border bg-muted p-2">
          <p role="status" className="text-sm font-medium">
            {t("ide.claude.changed")}
          </p>
          <Button variant="outline" onClick={() => onDismiss(file)}>
            {t("ide.claude.dismiss")}
          </Button>
        </div>
      ) : null}
      {names.map((name) => (
        <ConflictCard
          key={name}
          file={name}
          theirs={conflicts[name] ?? ""}
          onKeepMine={() => onKeepMine(name)}
          onTakeTheirs={() => onTakeTheirs(name)}
        />
      ))}
    </div>
  );
}
