import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import { PdfPicker } from "./PdfPicker";

interface CvImportStepProps {
  pending: boolean;
  /** Le refus du serveur (déjà en français) ; les fichiers choisis restent pour réessayer. */
  error: string | null;
  /** Les documents sont partis : le serveur les lit en arrière-plan. */
  imported: boolean;
  onImport: (documents: { cv: File; linkedin?: File }) => void;
}

/**
 * L'import du CV (PDF) et du profil LinkedIn (PDF, facultatif) du premier lancement. Rien ne part
 * tant que le CV manque ; un fichier qui n'est pas un PDF, ou de plus de 10 Mo, est refusé tout de
 * suite. L'étape se passe sans rien envoyer (c'est le bouton de la page qui avance).
 */
export function CvImportStep({ pending, error, imported, onImport }: CvImportStepProps) {
  const [cv, setCv] = useState<File | null>(null);
  const [linkedin, setLinkedin] = useState<File | null>(null);
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (pending || cv === null) return;
    onImport({ cv, ...(linkedin ? { linkedin } : {}) });
  };
  return (
    <form onSubmit={submit} aria-busy={pending} className="flex flex-col gap-4">
      <p className="text-muted-foreground">{t("onboarding.cv.intro")}</p>
      <p className="text-sm text-muted-foreground">{t("onboarding.cv.privacy")}</p>
      <PdfPicker label={t("onboarding.cv.cvLabel")} disabled={pending} onPick={setCv} />
      <PdfPicker label={t("onboarding.cv.linkedinLabel")} disabled={pending} onPick={setLinkedin} />
      {error ? <InlineError message={error} /> : null}
      {imported ? (
        <p role="status" className="text-sm">
          {t("onboarding.cv.done")}
        </p>
      ) : null}
      <Button type="submit" className="self-start" aria-disabled={pending || cv === null}>
        {pending ? t("onboarding.cv.pending") : t("onboarding.cv.submit")}
      </Button>
    </form>
  );
}
