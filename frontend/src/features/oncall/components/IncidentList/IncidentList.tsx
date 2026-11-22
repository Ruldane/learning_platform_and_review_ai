import { Link } from "react-router";
import { t } from "@/shared/i18n/t";

interface ListEntry {
  id: string;
  title: string;
  minute: number;
}

export function IncidentList({ incidents }: { incidents: ListEntry[] }) {
  return (
    <section className="flex flex-col gap-3" aria-labelledby="oncall-list">
      <h2 id="oncall-list" className="text-xl font-semibold">
        {t("oncall.incidents")}
      </h2>
      {incidents.length === 0 && <p>{t("oncall.noIncidents")}</p>}
      <ul className="flex flex-col gap-2">
        {incidents.map((incident) => (
          <li key={incident.id} className="flex flex-wrap items-center gap-2">
            <Link
              className="underline underline-offset-2"
              to={`/astreinte/${encodeURIComponent(incident.id)}`}
            >
              {incident.title}
            </Link>
            <span className="text-sm">{t("oncall.minute", { minute: incident.minute })}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}
