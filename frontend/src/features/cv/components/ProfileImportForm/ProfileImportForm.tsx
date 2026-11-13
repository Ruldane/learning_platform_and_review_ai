import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import { InlineError } from "@/shared/ui/states/InlineError";
import type { ProfileImportView } from "../viewTypes";
import { NoteField } from "./NoteField";
import { PdfField } from "./PdfField";

interface ProfileImportFormProps {
  pending: boolean;
  /** Message d'échec de l'envoi, déjà en français. */
  error: string | null;
  onSubmit: (documents: ProfileImportView) => void;
}

/**
 * Importer ses documents pour créer le profil maître : un CV en PDF (obligatoire), un profil
 * LinkedIn en PDF et une note (facultatifs). Un fichier qui n'est pas un PDF, ou de plus de 10 Mo,
 * est refusé tout de suite avec son message ; rien ne part tant que le CV manque.
 */
export function ProfileImportForm({ pending, error, onSubmit }: ProfileImportFormProps) {
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
      <Button type="submit" className="self-start" disabled={pending || cv === null}>
        {pending ? t("cv.import.pending") : t("cv.import.submit")}
      </Button>
    </form>
  );
}
