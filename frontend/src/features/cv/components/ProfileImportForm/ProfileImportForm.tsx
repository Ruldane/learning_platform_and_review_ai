import { useState, type FormEvent, type ReactNode } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ProfileImportView } from "../viewTypes";
import { NoteField } from "./NoteField";
import { PdfField } from "./PdfField";

interface ProfileImportFormProps {
  pending: boolean;
  launchMenu?: ReactNode;
  /** Upload failure message, already in French. */
  error: string | null;
  onSubmit: (documents: ProfileImportView) => void;
}

/**
 * Import your documents to create the master profile: a CV in PDF (required), a LinkedIn
 * profile in PDF and a note (optional). A file that is not a PDF, or over 10 MB, is refused at
 * once with its message; nothing is sent while the CV is missing.
 */
export function ProfileImportForm({
  pending,
  error,
  onSubmit,
  launchMenu,
}: ProfileImportFormProps) {
  const [cv, setCv] = useState<File | null>(null);
  const [linkedin, setLinkedin] = useState<File | null>(null);
  const [note, setNote] = useState("");

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (pending || cv === null) return;
    const trimmed = note.trim();
    onSubmit({ cv, ...(linkedin ? { linkedin } : {}), ...(trimmed ? { note: trimmed } : {}) });
  };

  return (
    <form
      onSubmit={submit}
      aria-label={t("cv.import.label")}
      aria-busy={pending}
      className="flex flex-col gap-4"
    >
      <p className="text-sm text-muted-foreground">{t("cv.import.privacy")}</p>
      <PdfField
        label={t("cv.import.cvLabel")}
        hint={t("cv.import.cvHint")}
        disabled={pending}
        onPick={setCv}
      />
      <PdfField label={t("cv.import.linkedinLabel")} disabled={pending} onPick={setLinkedin} />
      <NoteField value={note} disabled={pending} onChange={setNote} />
      {error ? <InlineError message={error} /> : null}
      {launchMenu}
      <Button type="submit" className="self-start" disabled={pending || cv === null}>
        {pending ? t("cv.import.pending") : t("cv.import.submit")}
      </Button>
    </form>
  );
}
