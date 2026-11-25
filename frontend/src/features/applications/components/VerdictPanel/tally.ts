import { t } from "@/shared/i18n/t";
import type { VoteValueView, VoteView } from "../viewTypes";

const countOf = (votes: VoteView[], value: VoteValueView): string => {
  const count = votes.filter((vote) => vote.vote === value).length;
  return t(`applications.verdictPanel.count.${value}.${count === 1 ? "one" : "many"}`, { count });
};

/** « 3 oui ; 1 non ; 0 peut-être »: the vote count, stated in words. */
export function tallyOf(votes: VoteView[]): string {
  return t("applications.verdictPanel.tally", {
    yes: countOf(votes, "yes"),
    no: countOf(votes, "no"),
    maybe: countOf(votes, "maybe"),
  });
}

/**
 * The sentence explaining the verdict, from the votes: « peut-être » is a real verdict when
 * at least three readers voted it, otherwise it is the absence of a majority.
 */
export function explanationOf(verdict: VoteValueView, votes: VoteView[]): string {
  const maybe = votes.filter((vote) => vote.vote === "maybe").length;
  if (verdict === "maybe" && maybe >= 3) {
    return t("applications.verdictPanel.explain.maybe_majority");
  }
  return t(`applications.verdictPanel.explain.${verdict}`);
}
