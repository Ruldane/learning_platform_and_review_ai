import { useState, type FormEvent } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { GithubClaimForm, SubmissionRefusalView, SubmissionView } from "../viewTypes";
import { GithubCommitFields } from "./GithubCommitFields";
import { submissionErrors } from "./rules";
import { SubmissionFields } from "./SubmissionFields";
import { useRefusal } from "./useRefusal";

interface SubmissionFormProps {
  onSubmit: (submission: SubmissionView) => void;
  /** Un rendu part : tout est désactivé jusqu'à la réponse. */
  busy: boolean;
  /** Ce que le serveur a refusé, rangé par champ ; un message s'efface dès que son champ change. */
  refusal?: SubmissionRefusalView | null;
  /**
   * Le point de départ des champs (le dernier rendu d'un projet à reprendre) ; les captures ne se
   * reprennent pas.
   */
  initial?: { repoUrl: string | null; description: string | null };
  github?: GithubClaimForm;
}

function useSubmissionDraft({
  onSubmit,
  busy,
  refusal = null,
  initial,
  github,
}: SubmissionFormProps) {
  const [repoUrl, setRepoUrl] = useState(initial?.repoUrl ?? "");
  const [description, setDescription] = useState(initial?.description ?? "");
  const [screenshots, setScreenshots] = useState<File[]>([]);
  const [attempted, setAttempted] = useState(false);
  const [sha, setSha] = useState("");
  const issued = github?.claim;
  const claim =
    issued?.repoUrl === repoUrl.trim() && issued.sha === sha.trim().toLowerCase() ? issued : null;
  const { refused, clear } = useRefusal(refusal);

  const errors = submissionErrors(repoUrl, description);
  // La description trop longue se signale dès la frappe ; le reste après une première tentative.
  const shown = attempted ? errors : { description: errors.description };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (busy || (sha && !claim)) return;
    setAttempted(true);
    if (Object.keys(errors).length > 0) return;
    onSubmit({
      repoUrl: repoUrl.trim() || null,
      description: description.trim() || null,
      screenshots,
      ...(claim ? { githubClaimId: claim.id } : {}),
    });
  };

  return {
    submit,
    sha,
    setSha,
    claim,
    waitingForClaim: Boolean(sha && !claim),
    fields: {
      repoUrl,
      description,
      screenshots,
      busy,
      errors: shown,
      refused,
      clear,
      onRepoUrl: setRepoUrl,
      onDescription: setDescription,
      onScreenshots: setScreenshots,
    },
  };
}

/** Le rendu avec le lien du dépôt, la description, les captures et l’attribution facultative. */
export function SubmissionForm(props: SubmissionFormProps) {
  const { busy, github } = props;
  const { submit, fields, sha, setSha, claim, waitingForClaim } = useSubmissionDraft(props);
  return (
    <form
      onSubmit={submit}
      noValidate
      aria-label={t("projects.submission.label")}
      aria-busy={busy}
      className="flex flex-col gap-4 rounded-xl border bg-card p-4"
    >
      <SubmissionFields {...fields} />
      {github && (
        <GithubCommitFields
          form={github}
          claim={claim}
          repoUrl={fields.repoUrl.trim()}
          sha={sha}
          onSha={setSha}
          busy={busy}
        />
      )}
      {waitingForClaim && (
        <p className="text-sm text-muted-foreground">{t("projects.github.waitingForCode")}</p>
      )}
      <Button type="submit" className="self-start" aria-disabled={busy || waitingForClaim}>
        {busy ? t("projects.submission.busy") : t("projects.submission.submit")}
      </Button>
    </form>
  );
}
