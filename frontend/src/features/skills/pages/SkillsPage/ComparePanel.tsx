import { useMemo, useState } from "react";
import { CompareTargetPicker } from "../../components/CompareTargetPicker";
import type { CompareTargetView } from "../../components/viewTypes";
import { usePostingChoices } from "../../hooks/usePostingChoices";
import { toPostingChoices } from "../../toView";
import { GoalCompare } from "./GoalCompare";
import { PostingCompare } from "./PostingCompare";

/**
 * L'onglet Comparaison : avec le poste cible de l'objectif, ou avec une offre analysée (choisie
 * dans la liste). Seule la cible ouverte lit ses données.
 */
export function ComparePanel() {
  const [target, setTarget] = useState<CompareTargetView>("goal");
  const [postingId, setPostingId] = useState<string | null>(null);
  const postings = usePostingChoices(target === "posting");
  const choices = useMemo(
    () => (postings.data ? toPostingChoices(postings.data) : []),
    [postings.data],
  );
  return (
    <div className="flex flex-col gap-4">
      <CompareTargetPicker
        target={target}
        onTarget={setTarget}
        postings={choices}
        postingId={postingId}
        onPosting={setPostingId}
      />
      {target === "goal" ? (
        <GoalCompare />
      ) : (
        <PostingCompare postings={postings} choices={choices} postingId={postingId} />
      )}
    </div>
  );
}
