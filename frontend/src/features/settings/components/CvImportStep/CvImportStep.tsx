import type { FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { CvDocuments } from "../viewTypes";
import { PdfPicker } from "./PdfPicker";
import { SendRow } from "./SendRow";

interface CvImportStepProps {
  /** Les deux PDF retenus, gardés par la page. */
  documents: CvDocuments;
  /** Une clé d'API existe : sans elle, rien ne peut être lu. */
  hasKey: boolean;
  pending: boolean;
  /** Le refus du serveur (déjà en français) ; les fichiers choisis restent pour réessayer. */
  error: string | null;
  /** Les documents sont partis : le serveur les lit en arrière-plan. */
  imported: boolean;
  onImport: (documents: { cv: File; linkedin?: File }) => void;
  /** Revenir à l'étape de la clé (sans clé, l'import n'est pas ouvert). */
  onGoToKey: () => void;
}

/**
 * L'import du CV (PDF) et du profil LinkedIn (PDF, facultatif) du premier lancement. Rien ne part
 * tant que le CV manque ou qu'aucune clé n'existe (la lecture n'aurait aucun modèle à appeler) :
 * la raison est dite et reliée au bouton. Un fichier qui n'est pas un PDF, ou de plus de 10 Mo,
 * est refusé tout de suite ; un LinkedIn refusé est dit, le CV partirait seul. L'étape se passe
 * sans rien envoyer (c'est le bouton de la page qui avance).
 */
export function CvImportStep(props: CvImportStepProps) {
  const { documents, hasKey, pending, error, imported, onImport, onGoToKey } = props;
  const { cv, linkedin } = documents;
  const reasons = [
    hasKey ? null : t("onboarding.cv.needKey"),
    hasKey && cv.file === null ? t("onboarding.cv.needCv") : null,
    linkedin.problem !== null ? t("onboarding.cv.linkedinLeftOut") : null,
  ].filter((text) => text !== null);
  const blocked = pending || cv.file === null || !hasKey;
  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (blocked || cv.file === null) return;
    onImport({ cv: cv.file, ...(linkedin.file ? { linkedin: linkedin.file } : {}) });
  };
  return (
    <form onSubmit={submit} aria-busy={pending} className="flex flex-col gap-4">
      <p className="text-muted-foreground">{t("onboarding.cv.intro")}</p>
      <p className="text-sm text-muted-foreground">{t("onboarding.cv.privacy")}</p>
      <PdfPicker
        label={t("onboarding.cv.cvLabel")}
        disabled={pending}
        choice={cv}
        onChange={documents.setCv}
      />
      <PdfPicker
        label={t("onboarding.cv.linkedinLabel")}
        disabled={pending}
        choice={linkedin}
        onChange={documents.setLinkedin}
      />
      {error ? <InlineError message={error} /> : null}
      {imported ? (
        <p role="status" className="text-sm">
          {t("onboarding.cv.done")}
        </p>
      ) : null}
      {cv.file !== null && !imported ? (
        <p className="text-sm text-muted-foreground">{t("onboarding.cv.notSent")}</p>
      ) : null}
      <SendRow
        pending={pending}
        blocked={blocked}
        hasKey={hasKey}
        reasons={reasons}
        onGoToKey={onGoToKey}
      />
    </form>
  );
}
