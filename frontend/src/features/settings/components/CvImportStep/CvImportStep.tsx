import type { FormEvent, ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { CvDocuments } from "../viewTypes";
import { PdfPicker } from "./PdfPicker";
import { SendRow } from "./SendRow";

interface CvImportStepProps {
  /** The two PDFs picked, kept by the page. */
  documents: CvDocuments;
  /** An API key exists: without one, nothing can be read. */
  hasKey: boolean;
  pending: boolean;
  launchMenu?: ReactNode;
  /** The server's refusal (already in French); the chosen files stay so the user can retry. */
  error: string | null;
  /** The documents have been sent: the server reads them in the background. */
  imported: boolean;
  onImport: (documents: { cv: File; linkedin?: File }) => void;
  /** Go back to the key step (without a key, the import is not open). */
  onGoToKey: () => void;
}

/**
 * Importing the CV (PDF) and the LinkedIn profile (PDF, optional) on first run. Nothing is sent
 * while the CV is missing or no key exists (reading would have no model to call):
 * the reason is stated and tied to the button. A file that is not a PDF, or larger than 10 MB,
 * is refused right away; a refused LinkedIn file is stated, the CV would go on its own. The step
 * sends nothing (the page's button moves on).
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
        launchMenu={props.launchMenu}
        pending={pending}
        blocked={blocked}
        hasKey={hasKey}
        reasons={reasons}
        onGoToKey={onGoToKey}
      />
    </form>
  );
}
