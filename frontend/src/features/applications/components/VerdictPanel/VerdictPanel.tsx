import type { Ref } from "react";
import { t } from "@/shared/i18n/t";
import { VoteLabel } from "../VoteLabel";
import type { ChangeView, ObjectionView, VoteValueView, VoteView } from "../viewTypes";
import { ChangeList } from "./ChangeList";
import { ObjectionList } from "./ObjectionList";
import { explanationOf, tallyOf } from "./tally";

interface VerdictPanelProps {
  verdict: VoteValueView | null;
  votes: VoteView[];
  objections: ObjectionView[];
  changes: ChangeView[];
  /** Le titre, pour que la page y place le focus quand le verdict arrive. */
  titleRef?: Ref<HTMLHeadingElement>;
}

/** Le verdict (majorité de 3 voix sur 4, sinon « peut-être »), les objections classées et les trois changements. */
export function VerdictPanel({ verdict, votes, objections, changes, titleRef }: VerdictPanelProps) {
  return (
    <section className="flex flex-col gap-4">
      <h2 ref={titleRef} tabIndex={-1} className="text-lg font-semibold outline-none">
        {t("applications.verdictPanel.title")}
      </h2>
      {verdict ? (
        <div className="flex flex-col gap-1">
          <p className="flex flex-wrap items-center gap-2 font-medium">
            {t("applications.verdictPanel.verdict")}
            <VoteLabel vote={verdict} />
          </p>
          <p className="text-sm">{explanationOf(verdict, votes)}</p>
          <p className="text-sm text-muted-foreground">{tallyOf(votes)}</p>
        </div>
      ) : null}
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">{t("applications.verdictPanel.objectionsTitle")}</h3>
        <ObjectionList objections={objections} />
      </div>
      <div className="flex flex-col gap-2">
        <h3 className="font-medium">{t("applications.verdictPanel.changesTitle")}</h3>
        <ChangeList changes={changes} />
      </div>
    </section>
  );
}
