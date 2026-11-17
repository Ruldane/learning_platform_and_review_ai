import { useId, useState } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface ConflictCardProps {
  file: string;
  /** La version de Claude (celle du serveur) : jamais appliquée sans ton choix. */
  theirs: string;
  onKeepMine: () => void;
  onTakeTheirs: () => void;
}

/**
 * Claude a changé un fichier où tu avais des retouches pas enregistrées. Tes retouches restent à
 * l'écran ; tu peux lire la version de Claude, puis garder la tienne ou prendre la sienne. Rien
 * n'est perdu sans ton geste.
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
            <Button variant="outline" className="w-fit" onClick={onTakeTheirs}>
              {t("ide.claude.takeTheirs")}
            </Button>
          </>
        ) : null}
      </div>
    </section>
  );
}
