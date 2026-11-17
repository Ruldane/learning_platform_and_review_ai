import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SubmissionForm } from "../../components/SubmissionForm";
import type { useSubmitProject } from "../../hooks/useSubmitProject";
import type { SubmissionItemView } from "../../toView";

interface SubmitSectionProps {
  submitter: ReturnType<typeof useSubmitProject>;
  /**
   * Le dernier rendu d'un projet à reprendre : le formulaire repart de son lien et de sa
   * description.
   */
  previous?: SubmissionItemView | null;
}

/**
 * Le rendu du projet : le formulaire, verrouillé pendant l'envoi, et le refus qui n'est pas d'un
 * champ.
 */
export function SubmitSection({ submitter, previous = null }: SubmitSectionProps) {
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
        refusal={submitter.refusal}
        onSubmit={(submission) => void submitter.submit(submission)}
      />
      {submitter.message ? <InlineError message={submitter.message} /> : null}
    </section>
  );
}
