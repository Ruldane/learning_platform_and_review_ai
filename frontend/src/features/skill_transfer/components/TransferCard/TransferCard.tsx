import { useId, type ReactNode, type Ref } from "react";
import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { TransferView } from "../viewTypes";
import { TransferAnswerForm } from "./TransferAnswerForm";
import { TransferResult } from "./TransferResult";

interface Props {
  view: TransferView;
  busy: boolean;
  headingRef: Ref<HTMLHeadingElement>;
  onPrepare: () => void;
  onAnswer: (answer: string) => void;
}

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "long", timeZone: "UTC" });

function renderAction({ view, busy, onPrepare, onAnswer }: Props): ReactNode {
  const action = view.action;
  if (action.kind === "answer") {
    return <TransferAnswerForm view={action.answer} busy={busy} onAnswer={onAnswer} />;
  }
  if (action.kind === "result") return <TransferResult assessment={action.result} />;
  if (action.kind === "prepare") {
    return (
      <Button type="button" className="justify-self-start" disabled={busy} onClick={onPrepare}>
        {t(action.retry ? "skillTransfer.retryPrepare" : "skillTransfer.prepare")}
      </Button>
    );
  }
  return <p role="status" className="text-sm">{t(`skillTransfer.${action.text}`)}</p>;
}

export function TransferCard(props: Props) {
  const { view, headingRef } = props;
  const title = useId();
  return (
    <article aria-labelledby={title} className="grid gap-3 rounded-xl border bg-card p-4">
      <h3 id={title} className="font-semibold" tabIndex={-1} ref={headingRef}>
        {view.skill}
      </h3>
      <p className="text-sm">{view.proof}</p>
      <time dateTime={view.dueOn} className="text-sm text-muted-foreground">
        {t("skillTransfer.due", { date: dateFormat.format(new Date(view.dueOn)) })}
      </time>
      {renderAction(props)}
    </article>
  );
}
