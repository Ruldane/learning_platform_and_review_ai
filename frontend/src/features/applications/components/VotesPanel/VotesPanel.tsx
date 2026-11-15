import { t } from "@/shared/i18n/t";
import { agentIdentity } from "@/shared/session-ui";
import { VoteLabel } from "../VoteLabel";
import type { VoteView } from "../viewTypes";

/** Les quatre votes motivés, chacun avec l'objection principale de sa persona ; le vote est écrit, jamais une couleur seule. */
export function VotesPanel({ votes }: { votes: VoteView[] }) {
  return (
    <section aria-label={t("applications.votesPanel.label")} className="flex flex-col gap-3">
      <h3 className="text-lg font-semibold">{t("applications.votesPanel.title")}</h3>
      <ul className="flex flex-col gap-3">
        {votes.map((vote) => {
          const who = agentIdentity(vote.persona);
          return (
            <li
              key={vote.persona}
              style={{ borderLeftColor: who.color }}
              className="flex flex-col gap-2 rounded-xl border border-l-4 bg-card p-3"
            >
              <h4 className="font-medium">
                {who.name} <span className="text-sm text-muted-foreground">({who.role})</span>
              </h4>
              <dl className="flex flex-col gap-1 text-sm">
                <div className="flex flex-wrap items-center gap-2">
                  <dt className="font-medium">{t("applications.votesPanel.vote")}</dt>
                  <dd>
                    <VoteLabel vote={vote.vote} />
                  </dd>
                </div>
                <div>
                  <dt className="font-medium">{t("applications.votesPanel.objection")}</dt>
                  <dd>{vote.objection}</dd>
                </div>
                <div>
                  <dt className="font-medium">{t("applications.votesPanel.reason")}</dt>
                  <dd>{vote.reason}</dd>
                </div>
              </dl>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
