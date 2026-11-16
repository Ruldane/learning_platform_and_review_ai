import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { SubmissionView } from "../viewTypes";
import { DescriptionField } from "./DescriptionField";
import { RepoUrlField } from "./RepoUrlField";
import { submissionErrors } from "./rules";
import { ScreenshotPicker } from "./ScreenshotPicker";

interface SubmissionFormProps {
  onSubmit: (submission: SubmissionView) => void;
  /** Un rendu part : tout est désactivé jusqu'à la réponse. */
  busy: boolean;
}

/**
 * Rendre un projet : un lien de dépôt et/ou une description (4 000 caractères au plus, compteur),
 * jusqu'à 5 captures. Chaque champ à corriger a son message ; le serveur reste l'autorité.
 */
export function SubmissionForm({ onSubmit, busy }: SubmissionFormProps) {
  const [repoUrl, setRepoUrl] = useState("");
  const [description, setDescription] = useState("");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [attempted, setAttempted] = useState(false);

  const errors = submissionErrors(repoUrl, description);
  // La description trop longue se signale dès la frappe ; le reste après une première tentative.
  const shown = attempted ? errors : { description: errors.description };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy) return;
    setAttempted(true);
    if (Object.keys(errors).length > 0) return;
    onSubmit({
      repoUrl: repoUrl.trim() || null,
      description: description.trim() || null,
      screenshots,
    });
  };

  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("projects.submission.label")}
      aria-busy={busy}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4"
    >
      <RepoUrlField value={repoUrl} disabled={busy} error={shown.repoUrl} onChange={setRepoUrl} />
      <DescriptionField
        value={description}
        disabled={busy}
        error={shown.description}
        onChange={setDescription}
      />
      <ScreenshotPicker files={screenshots} disabled={busy} onChange={setScreenshots} />
      {shown.missing ? (
        <p role="alert" className="text-sm text-destructive">
          {shown.missing}
        </p>
      ) : null}
      <Button type="submit" className="self-start" disabled={busy}>
        {busy ? t("projects.submission.busy") : t("projects.submission.submit")}
      </Button>
    </form>
  );
}
