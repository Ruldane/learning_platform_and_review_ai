import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { ConflictCard } from "./ConflictCard";

interface ClaudeChangesProps {
  /** Le fichier ouvert dans l'éditeur. */
  file: string;
  /** Les fichiers que Claude a changés et que l'éditeur a chargés tels quels. */
  notices: string[];
  /** Les fichiers où Claude et toi avez changé : nom -> version de Claude. */
  conflicts: Record<string, string>;
  onDismiss: (file: string) => void;
  onKeepMine: (file: string) => void;
  onTakeTheirs: (file: string) => void;
}

/**
 * Ce que Claude a fait aux fichiers pendant la séance : un message pour le fichier ouvert qu'il a
 * modifié (l'éditeur montre sa version), et une carte de choix pour chaque fichier en conflit.
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
