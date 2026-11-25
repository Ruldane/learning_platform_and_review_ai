import { t } from "@/shared/i18n/t";
import { ExternalLink } from "@/shared/ui/ExternalLink";
import { formatInstant } from "../../format";
import type { SubmissionItemView } from "../../toView";

/** A submission in the history: its date, repository, description and its screenshot thumbnails. */
export function SubmissionItem({ submission }: { submission: SubmissionItemView }) {
  const when = formatInstant(submission.at);
  return (
    <li className="flex min-w-0 flex-col gap-2 rounded-xl border bg-card p-4 text-sm [overflow-wrap:anywhere]">
      <h3 className="font-medium">{t("projects.page.submittedOn", { when })}</h3>
      {submission.repoUrl ? (
        <p>
          {t("projects.page.repo")} :{" "}
          <ExternalLink href={submission.repoUrl}>{submission.repoUrl}</ExternalLink>
        </p>
      ) : null}
      {submission.description ? (
        <p className="whitespace-pre-line">{submission.description}</p>
      ) : null}
      {submission.screenshots.length > 0 ? (
        <ul aria-label={t("projects.page.shots", { when })} className="flex flex-wrap gap-2">
          {submission.screenshots.map((shot) => (
            <li key={shot.number}>
              <img
                src={shot.src}
                alt={t("projects.page.shot", { number: shot.number, when })}
                loading="lazy"
                className="size-20 rounded border object-cover"
              />
            </li>
          ))}
        </ul>
      ) : null}
    </li>
  );
}
