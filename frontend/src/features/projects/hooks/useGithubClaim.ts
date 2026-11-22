import { useMutation } from "@tanstack/react-query";
import { errorMessage } from "@/shared/api/errors";
import { requestGithubClaim } from "../api";
import type { GithubClaimForm, GithubCommitSelection } from "../types";

export function useGithubClaim(projectId: string): GithubClaimForm {
  const mutation = useMutation({
    mutationFn: (selection: GithubCommitSelection) => requestGithubClaim(projectId, selection),
  });
  const { data, variables } = mutation;
  return {
    claim:
      data && variables
        ? { ...variables, id: data.id, code: data.code, profileUrl: data.profile_url }
        : null,
    pending: mutation.isPending,
    error: mutation.error ? errorMessage(mutation.error) : null,
    request: mutation.mutate,
  };
}
