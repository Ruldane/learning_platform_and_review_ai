import { t } from "@/shared/i18n/t";
import { Button } from "@/shared/ui/button";
import type { Appeal, AppealDecision } from "../../api";

export type AppealAction = "review" | AppealDecision;

interface Props {
  row: Appeal;
  busy: boolean;
  onAction: (action: AppealAction) => void;
}

export function AppealActions({ row, busy, onAction }: Props) {
  if (row.state === "draft" || row.state === "failed") {
    return (
      <Button className="justify-self-start" disabled={busy} onClick={() => onAction("review")}>
        {t(row.state === "failed" ? "gradeAppeals.retry" : "gradeAppeals.review")}
      </Button>
    );
  }
  if (row.state === "ready") {
    return (
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" disabled={busy} onClick={() => onAction("keep_original")}>{t("gradeAppeals.keep")}</Button>
        <Button disabled={busy} onClick={() => onAction("accept_second")}>{t("gradeAppeals.accept")}</Button>
      </div>
    );
  }
  if (row.decision) {
    return <p className="font-semibold">{t(row.decision === "accept_second" ? "gradeAppeals.accepted" : "gradeAppeals.kept")}</p>;
  }
  return null;
}
