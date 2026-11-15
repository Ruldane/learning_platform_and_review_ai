import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import { VoteLabel } from "../VoteLabel";
import type { VoteChangeView, VoteValueView } from "../viewTypes";

const WEIGHT: Record<VoteValueView, number> = { non: 0, peut_etre: 1, oui: 2 };

/** « Plus favorable » quand le vote monte (non, peut-être, oui), « Moins favorable » quand il descend. */
function evolution(change: VoteChangeView): "same" | "better" | "worse" {
  const delta = WEIGHT[change.after] - WEIGHT[change.before];
  if (delta === 0) return "same";
  return delta > 0 ? "better" : "worse";
}

/** Le vote de chaque persona avant et après, avec l'évolution dite en mots. */
export function VoteDiffTable({ votes }: { votes: VoteChangeView[] }) {
  return (
    <table aria-label={t("applications.diffView.votesLabel")} className="w-full text-left text-sm">
      <thead>
        <tr className="border-b">
          <th scope="col" className="py-1 pr-3 font-medium">
            {t("applications.diffView.persona")}
          </th>
          <th scope="col" className="py-1 pr-3 font-medium">
            {t("applications.diffView.before")}
          </th>
          <th scope="col" className="py-1 pr-3 font-medium">
            {t("applications.diffView.after")}
          </th>
          <th scope="col" className="py-1 font-medium">
            {t("applications.diffView.change")}
          </th>
        </tr>
      </thead>
      <tbody>
        {votes.map((change) => (
          <tr key={change.persona} className="border-b last:border-0">
            <th scope="row" className="py-2 pr-3 font-medium">
              {agentIdentity(change.persona).name}
            </th>
            <td className="py-2 pr-3">
              <VoteLabel vote={change.before} />
            </td>
            <td className="py-2 pr-3">
              <VoteLabel vote={change.after} />
            </td>
            <td className="py-2">{t(`applications.diffView.${evolution(change)}`)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
