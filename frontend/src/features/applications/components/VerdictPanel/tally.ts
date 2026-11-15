import { t } from "@/shared/i18n/t";
import type { VoteValueView, VoteView } from "../viewTypes";

const countOf = (votes: VoteView[], value: VoteValueView): string => {
  const count = votes.filter((vote) => vote.vote === value).length;
  return t(`applications.verdictPanel.count.${value}.${count === 1 ? "one" : "many"}`, { count });
};

/** « 3 oui ; 1 non ; 0 peut-être » : le décompte des voix, dit en mots. */
export function tallyOf(votes: VoteView[]): string {
  return t("applications.verdictPanel.tally", {
    oui: countOf(votes, "oui"),
    non: countOf(votes, "non"),
    peut_etre: countOf(votes, "peut_etre"),
  });
}
