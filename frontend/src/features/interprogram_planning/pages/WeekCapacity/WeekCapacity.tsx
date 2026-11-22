import { t } from "@/shared/i18n/t";
import type { Week } from "../../api";
import { formatDay } from "../../dates";

export function WeekCapacity({ days }: { days: Week["days"] }) {
  return (
    <div className="overflow-auto">
      <table className="w-full text-left text-sm">
        <caption className="mb-2 text-left font-semibold">
          {t("interprogramPlanning.capacity")}
        </caption>
        <thead>
          <tr>
            <th scope="col">{t("interprogramPlanning.day")}</th>
            <th scope="col">{t("interprogramPlanning.available")}</th>
            <th scope="col">{t("interprogramPlanning.reserved")}</th>
            <th scope="col">{t("interprogramPlanning.proposed")}</th>
          </tr>
        </thead>
        <tbody>
          {days.map((day) => (
            <tr key={day.date} className="border-t border-border">
              <th scope="row" className="py-1 font-medium">
                {formatDay(day.date)}
              </th>
              <td>{day.capacity_minutes}</td>
              <td>{day.reserved_minutes}</td>
              <td>{day.planned_minutes}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
