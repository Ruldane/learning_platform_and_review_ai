import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { BlindRun } from "../../api";
import { BlindVerdict } from "../../components/BlindVerdict";
import { toVerdict } from "../../toView";

const dateFormat = new Intl.DateTimeFormat("en-GB", { dateStyle: "short", timeStyle: "short" });

interface Props {
  run: BlindRun;
  busy: boolean;
  evaluate: () => void;
}

export function BlindRunCard({ run, busy, evaluate }: Props) {
  const verdict = toVerdict(run);
  return (
    <article className="grid gap-3 rounded-xl border bg-card p-4">
      <h3 className="font-semibold">{run.rubric.title}</h3>
      <time dateTime={run.created_at} className="text-sm text-muted-foreground">
        {dateFormat.format(new Date(run.created_at))}
      </time>
      {run.stage === "draft" || run.stage === "failed" ? (
        <Button className="justify-self-start" disabled={busy} onClick={evaluate}>
          {t(run.stage === "draft" ? "blindAssessment.evaluate" : "blindAssessment.retry")}
        </Button>
      ) : null}
      {run.stage === "evaluating" ? <p role="status">{t("blindAssessment.running")}</p> : null}
      {verdict ? <BlindVerdict result={verdict} /> : null}
    </article>
  );
}
