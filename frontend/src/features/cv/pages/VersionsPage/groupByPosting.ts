import type { PostingSummaryOut, VersionOut } from "../../types";

export interface PostingGroup {
  postingId: string;
  /** « Titre, Entreprise » ; `null` si l'offre n'est plus connue. */
  label: string | null;
  /** Du plus récent au plus ancien. */
  versions: VersionOut[];
}

const labelOf = (posting: PostingSummaryOut | undefined): string | null => {
  if (posting === undefined) return null;
  return [posting.title, posting.company].filter((part) => part).join(", ") || null;
};

/** Les versions regroupées par offre, l'offre la plus récemment travaillée en premier. */
export function groupByPosting(
  versions: VersionOut[],
  postings: PostingSummaryOut[],
): PostingGroup[] {
  const groups = new Map<string, VersionOut[]>();
  for (const version of versions) {
    groups.set(version.posting_id, [...(groups.get(version.posting_id) ?? []), version]);
  }
  const newest = (list: VersionOut[]) => Math.max(...list.map((v) => Date.parse(v.created_at)));
  return [...groups.entries()]
    .map(([postingId, list]) => ({
      postingId,
      label: labelOf(postings.find((posting) => posting.id === postingId)),
      versions: [...list].sort((a, b) => b.number - a.number),
    }))
    .sort((a, b) => newest(b.versions) - newest(a.versions));
}
