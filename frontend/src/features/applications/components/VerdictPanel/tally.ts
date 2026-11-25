import { t } from "@/shared/i18n/t";
import type { VoteValueView, VoteView } from "../viewTypes";

const countOf = (votes: VoteView[], value: VoteValueView): string => {
  const count = votes.filter((vote) => vote.vote === value).length;
  return t(`applications.verdictPanel.count.${value}.${count === 1 ? "one" : "many"}`, { count });
};

/** « 3 oui ; 1 non ; 0 peut-être » : le décompte des voix, dit en mots. */
export function tallyOf(votes: VoteView[]): string {
  return t("applications.verdictPanel.tally", {
    yes: countOf(votes, "yes"),
    no: countOf(votes, "no"),
    maybe: countOf(votes, "maybe"),
  });
}

/**
 * La phrase qui explique le verdict, d'après les voix : « peut-être » est un vrai verdict quand
 * trois lecteurs au moins l'ont voté, sinon c'est l'absence de majorité.
 */
export function explanationOf(verdict: VoteValueView, votes: VoteView[]): string {
  const maybe = votes.filter((vote) => vote.vote === "maybe").length;
  if (verdict === "maybe" && maybe >= 3) {
    return t("applications.verdictPanel.explain.maybe_majority");
  }
  return t(`applications.verdictPanel.explain.${verdict}`);
}
