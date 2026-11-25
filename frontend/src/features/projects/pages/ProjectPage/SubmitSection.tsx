import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SubmissionForm } from "../../components/SubmissionForm";
import { useGithubClaim } from "../../hooks/useGithubClaim";
import type { useSubmitProject } from "../../hooks/useSubmitProject";
import type { SubmissionItemView } from "../../toView";

interface SubmitSectionProps {
  projectId: string;
  submitter: ReturnType<typeof useSubmitProject>;
  /**
   * The latest submission of a project to resume: the form starts again from its link and
   * description.
   */
  previous?: SubmissionItemView | null;
}

/**
 * The project submission: the form, locked during sending, and any refusal not tied to a
 * field.
 */
export function SubmitSection({ projectId, submitter, previous = null }: SubmitSectionProps) {
  const github = useGithubClaim(projectId);
  return (
    <section aria-labelledby="project-submit" className="flex flex-col gap-3">
      <h2 id="project-submit" className="text-lg font-medium">
        {t("projects.page.submitTitle")}
      </h2>
      {previous && previous.screenshots.length > 0 ? (
        <p className="text-sm text-muted-foreground">{t("projects.page.screenshotsNotCarried")}</p>
      ) : null}
      <SubmissionForm
        initial={
          previous ? { repoUrl: previous.repoUrl, description: previous.description } : undefined
        }
        busy={submitter.pending}
        github={github}
        refusal={submitter.refusal}
        onSubmit={(submission) => void submitter.submit(submission)}
      />
      {submitter.message ? <InlineError message={submitter.message} /> : null}
    </section>
  );
}
