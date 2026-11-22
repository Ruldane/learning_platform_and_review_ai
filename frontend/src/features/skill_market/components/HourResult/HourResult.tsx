import { Link } from "react-router";
import { t } from "@/shared/i18n/t";
import type { HourView as Simulation } from "../viewTypes";

export function HourResult({ value }: { value: Simulation }) {
  return (
    <section
      aria-labelledby="hour-result"
      className="flex flex-col gap-2 rounded-lg border bg-muted/30 p-4"
    >
      <h2 id="hour-result" className="font-semibold">
        {t("skillMarket.hour", { name: value.skill })}
      </h2>
      {value.chapter ? <p>{value.chapter}</p> : <p>{t("skillMarket.noChapter")}</p>}
      {value.progress_percent !== null && value.remaining_minutes !== null ? (
        <p>
          {t("skillMarket.progress", {
            value: value.progress_percent,
            minutes: value.remaining_minutes,
          })}
        </p>
      ) : null}
      {value.covered_after !== null ? (
        <p>
          {t("skillMarket.coverage", { before: value.covered_before, after: value.covered_after })}
        </p>
      ) : null}
      {value.lesson_id ? (
        <Link
          to={"/apprendre/lecons/" + encodeURIComponent(value.lesson_id)}
          className="w-fit underline"
        >
          {t("skillMarket.chapter")}
        </Link>
      ) : null}
    </section>
  );
}
