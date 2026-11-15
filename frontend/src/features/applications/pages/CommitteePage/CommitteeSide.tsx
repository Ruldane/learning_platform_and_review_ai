import { useEffect, useRef, useState } from "react";
import { t } from "@/shared/i18n/t";
import { SideTabs } from "@/shared/session-ui";
import { CommitteeDiffView } from "../../components/CommitteeDiffView";
import { VerdictPanel } from "../../components/VerdictPanel";
import { VotesPanel } from "../../components/VotesPanel";
import type { CommitteeView } from "../../types";
import { ResultGate } from "./ResultGate";

const TAB_IDS = ["votes", "verdict", "diff"] as const;
type Tab = (typeof TAB_IDS)[number];

const isTab = (id: string): id is Tab => TAB_IDS.some((tab) => tab === id);

/**
 * La colonne de droite : Votes, Verdict, Avant / après. Le verdict est l'onglet d'arrivée. Quand le
 * comité se termine sous les yeux de January et que le focus s'est perdu (la note « le comité
 * délibère » vient de disparaître), le titre du verdict le reçoit.
 */
export function CommitteeSide({ view }: { view: CommitteeView }) {
  const [tab, setTab] = useState<Tab>("verdict");
  const title = useRef<HTMLHeadingElement>(null);
  const before = useRef(view.status);

  useEffect(() => {
    const arrived = before.current === "running" && view.status === "done";
    before.current = view.status;
    const lost = document.activeElement === document.body || document.activeElement === null;
    if (arrived && lost && tab === "verdict") title.current?.focus();
  }, [view.status, tab]);

  return (
    <SideTabs
      label={t("applications.committeeTabs.label")}
      tabs={TAB_IDS.map((id) => ({ id, label: t(`applications.committeeTabs.${id}`) }))}
      active={tab}
      onChange={(id) => {
        if (isTab(id)) setTab(id);
      }}
      panels={{
        votes: (
          <ResultGate status={view.status}>
            <VotesPanel votes={view.votes} />
          </ResultGate>
        ),
        verdict: (
          <ResultGate status={view.status}>
            <VerdictPanel
              verdict={view.verdict}
              votes={view.votes}
              objections={view.objections}
              changes={view.changes}
              titleRef={title}
            />
          </ResultGate>
        ),
        diff: (
          <ResultGate status={view.status}>
            <CommitteeDiffView diff={view.diff} />
          </ResultGate>
        ),
      }}
    />
  );
}
