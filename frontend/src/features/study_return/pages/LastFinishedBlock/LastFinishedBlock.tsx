import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { LastBlock } from "../../api";
import { formatDate, trainingUrl } from "../../dates";

export function LastFinishedBlock({ value }: { value: LastBlock }) {
  const isTraining = value.kind === "training";
  const url = isTraining
    ? trainingUrl(value.id)
    : `/etudier/session/${encodeURIComponent(value.id)}`;
  return (
    <div>
      <h3 className="font-medium">{t("studyReturn.lastBlock")}</h3>
      <Link className="underline" to={url}>
        {t("studyReturn.finished", {
          title: value.title ?? t(isTraining ? "studyReturn.training" : "studyReturn.guided"),
          date: formatDate(value.ended_at),
          minutes: value.minutes,
        })}
      </Link>
    </div>
  );
}
