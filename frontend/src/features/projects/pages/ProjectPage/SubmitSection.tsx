import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { SubmissionForm } from "../../components/SubmissionForm";
import type { useSubmitProject } from "../../hooks/useSubmitProject";

/** Le rendu du projet : le formulaire, verrouillé pendant l'envoi, et le refus qui n'est pas d'un champ. */
export function SubmitSection({ submitter }: { submitter: ReturnType<typeof useSubmitProject> }) {
  return (
    <section aria-labelledby="project-submit" className="flex flex-col gap-3">
      <h2 id="project-submit" className="text-lg font-medium">
        {t("projects.page.submitTitle")}
      </h2>
      <SubmissionForm
        busy={submitter.pending}
        refusal={submitter.refusal}
        onSubmit={(submission) => void submitter.submit(submission)}
      />
      {submitter.message ? <InlineError message={submitter.message} /> : null}
    </section>
  );
}
