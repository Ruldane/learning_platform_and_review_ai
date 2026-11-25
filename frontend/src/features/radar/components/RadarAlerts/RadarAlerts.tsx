import { AlertTriangle } from "lucide-react";
import { t } from "@/shared/i18n/t";
import type { RadarAlertView } from "../viewTypes";

interface RadarAlertsProps {
  alerts: RadarAlertView[];
}

/** Skills in high demand and absent from the program: the server's message, as is. */
export function RadarAlerts({ alerts }: RadarAlertsProps) {
  return (
    <section aria-labelledby="radar-alerts" className="flex flex-col gap-2">
      <h2 id="radar-alerts" className="text-lg font-medium">
        {t("radar.alerts.title")}
      </h2>
      {alerts.length === 0 ? (
        <p className="text-muted-foreground">{t("radar.alerts.none")}</p>
      ) : (
        <ul aria-label={t("radar.alerts.label")} className="flex flex-col gap-2">
          {alerts.map((alert) => (
            <li
              key={alert.skill}
              className="flex items-start gap-2 rounded-lg border border-amber-500/60 bg-amber-500/10 p-3 text-sm"
            >
              <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span>
                <strong>{alert.skill}</strong>
                {" : "}
                {alert.message}
              </span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
