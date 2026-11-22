import { useQuery } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { t } from "@/shared/i18n/t";
import { InlineError } from "@/shared/ui/states/InlineError";
import { fetchGithubProofs } from "../../api";
import { projectKeys } from "../../queryKeys";

export function ProjectGithubProofs({ projectId }: { projectId: string }) {
  const proofs = useQuery({
    queryKey: projectKeys.github(projectId),
    queryFn: ({ signal }) => fetchGithubProofs(projectId, signal),
  });
  if (proofs.isError) return <InlineError message={errorMessage(proofs.error)} />;
  if (!proofs.data?.length) return null;
  return (
    <section aria-labelledby="project-github-proofs" className="flex flex-col gap-2">
      <h2 id="project-github-proofs" className="text-lg font-medium">
        {t("projects.github.proofs")}
      </h2>
      <ul className="flex flex-col gap-1">
        {proofs.data.map(({ commit_url: url, sha }) => (
          <li key={sha}>
            <a href={url} target="_blank" rel="noopener noreferrer" className="underline">
              {t("projects.github.commitLink", { sha: sha.slice(0, 8) })}
            </a>
          </li>
        ))}
      </ul>
    </section>
  );
}
