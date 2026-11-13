import { useNavigate } from "react-router";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { useStartStudy } from "../../hooks/useStartStudy";
import type { StudySessionOut } from "../../types";

/**
 * « Commencer un nouveau bloc » depuis une session arrêtée : le départ part d'ici (le back range
 * ou annule la session arrêtée), jamais par l'accueil, qui ramènerait à cette session. Sans bloc
 * prévu aujourd'hui, l'accueil propose de choisir une leçon.
 */
export function NewBlockStart({ mode }: { mode: StudySessionOut["mode"] }) {
  const navigate = useNavigate();
  const starter = useStartStudy(() => void navigate("/etudier/session"));
  return (
    <div className="flex flex-col gap-2">
      <Button
        variant="outline"
        disabled={starter.pending}
        onClick={() => void starter.start({ mode })}
      >
        {t("study.session.newBlock")}
      </Button>
      {starter.error ? <InlineError message={starter.error} /> : null}
    </div>
  );
}
