import { useId, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";

interface SendRowProps {
  pending: boolean;
  launchMenu?: ReactNode;
  /** Rien ne part : l'action est ignorée (`aria-disabled`, le focus reste sur le bouton). */
  blocked: boolean;
  hasKey: boolean;
  /** Ce qui empêche ou nuance l'envoi, dit et relié au bouton ; vide : rien à dire. */
  reasons: string[];
  onGoToKey: () => void;
}

/** « Importer mes documents », la voie vers la clé quand il n'y en a pas, et les raisons dites. */
export function SendRow({
  pending,
  blocked,
  hasKey,
  reasons,
  onGoToKey,
  launchMenu,
}: SendRowProps) {
  const reasonId = useId();
  return (
    <>
      <div className="flex flex-wrap items-end gap-3">
        {hasKey ? launchMenu : null}
        <Button
          type="submit"
          aria-disabled={blocked}
          aria-describedby={reasons.length > 0 ? reasonId : undefined}
        >
          {pending ? t("onboarding.cv.pending") : t("onboarding.cv.submit")}
        </Button>
        {hasKey ? null : (
          <Button type="button" variant="outline" onClick={onGoToKey}>
            {t("onboarding.cv.goToKey")}
          </Button>
        )}
      </div>
      {reasons.length > 0 ? (
        <p id={reasonId} className="text-sm text-muted-foreground">
          {reasons.join(" ")}
        </p>
      ) : null}
    </>
  );
}
