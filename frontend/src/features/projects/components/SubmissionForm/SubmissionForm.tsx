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
  /** A submission is going out: everything is disabled until the response. */
  busy: boolean;
  /** What the server refused, by field; a message clears as soon as its field changes. */
  refusal?: SubmissionRefusalView | null;
  /**
   * The starting point of the fields (the last submission of a project to resume); the screenshots
   * are not resumed.
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
  // An over-long description is flagged while typing; the rest after a first attempt.
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

/** The submission with the repository link, description, screenshots and optional credit. */
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
