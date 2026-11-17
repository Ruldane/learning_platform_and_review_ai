import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { SubmissionRefusalView, SubmissionView } from "../viewTypes";
import { submissionErrors } from "./rules";
import { SubmissionFields } from "./SubmissionFields";
import { useRefusal } from "./useRefusal";

interface SubmissionFormProps {
  onSubmit: (submission: SubmissionView) => void;
  /** Un rendu part : tout est désactivé jusqu'à la réponse. */
  busy: boolean;
  /** Ce que le serveur a refusé, rangé par champ ; un message s'efface dès que son champ change. */
  refusal?: SubmissionRefusalView | null;
  /** Le point de départ des champs (le dernier rendu d'un projet à reprendre) ; les captures ne se reprennent pas. */
  initial?: { repoUrl: string | null; description: string | null };
}

/**
 * Rendre un projet : un lien de dépôt et/ou une description (4 000 caractères au plus, compteur),
 * jusqu'à 5 captures. Chaque champ à corriger a son message ; le serveur reste l'autorité.
 */
export function SubmissionForm({ onSubmit, busy, refusal = null, initial }: SubmissionFormProps) {
  const [repoUrl, setRepoUrl] = useState(initial?.repoUrl ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [attempted, setAttempted] = useState(false);
  const { refused, clear } = useRefusal(refusal);

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
      <SubmissionFields
        repoUrl={repoUrl}
        description={description}
        screenshots={screenshots}
        busy={busy}
        errors={shown}
        refused={refused}
        clear={clear}
        onRepoUrl={setRepoUrl}
        onDescription={setDescription}
        onScreenshots={setScreenshots}
      />
      <Button type="submit" className="self-start" aria-disabled={busy}>
        {busy ? t("projects.submission.busy") : t("projects.submission.submit")}
      </Button>
    </form>
  );
}
