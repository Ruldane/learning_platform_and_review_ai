import { useEffect, useRef, useState } from "react";
import type { MessageKey } from "@/shared/i18n/t";
import { t } from "@/shared/i18n/t";

/** Shape of the `GET /health` report (generated types; not imported: the splitting rule). */
interface HealthReportView {
  status: "ok" | "degraded" | "down";
  checks: Record<string, { ok: boolean; detail: string }>;
}

interface ServiceChecklistProps {
  report?: HealthReportView;
  isLoading: boolean;
  /** The last read failed (the next round retries on its own). */
  isError: boolean;
}

const SERVICES = ["db", "llm", "qdrant", "ollama", "searxng"] as const;
type KnownService = (typeof SERVICES)[number];

const isKnown = (service: string): service is KnownService =>
  (SERVICES as readonly string[]).includes(service);

const label = (service: string): string =>
  isKnown(service) ? t(`onboarding.health.services.${service}` as MessageKey) : service;

/** A model's key is asked only at step 3: its absence is not an outage here. */
function stateText(service: string, ok: boolean): string {
  if (ok) return t("onboarding.health.ok");
  return service === "llm" ? t("onboarding.health.keyLater") : t("onboarding.health.down");
}

/** Services that respond again since the previous read, stated in a single text. */
function useRecovered(report?: HealthReportView): string {
  const previous = useRef<Record<string, boolean>>({});
  const [text, setText] = useState("");
  useEffect(() => {
    const checks = Object.entries(report?.checks ?? {});
    const back = checks.filter(([name, { ok }]) => ok && previous.current[name] === false);
    previous.current = Object.fromEntries(checks.map(([name, { ok }]) => [name, ok]));
    if (back.length > 0) {
      setText(
        t("onboarding.health.recovered", {
          services: back.map(([name]) => label(name)).join(", "),
        }),
      );
    }
  }, [report]);
  return text;
}

/**
 * A state written per service (never colour alone). Services unknown to the front keep
 * their raw name; the back end's detail (in French, without secrets) follows for a service down. A
 * single `status` zone, always on the page: its text changes only at useful moments (read
 * impossible, check in progress, service back), not at every reread.
 */
export function ServiceChecklist({ report, isLoading, isError }: ServiceChecklistProps) {
  const checks = Object.entries(report?.checks ?? {});
  const recovered = useRecovered(report);
  const tone = isError ? "text-destructive" : "text-muted-foreground";
  const checking = isLoading && checks.length === 0 && !isError;
  const announcement = (() => {
    if (isError) return t("onboarding.health.unreachable");
    return checking ? t("onboarding.health.checking") : recovered;
  })();
  return (
    <div className="flex flex-col gap-2">
      {checks.length > 0 ? (
        <ul aria-label={t("onboarding.health.list")} className="flex flex-col gap-1.5">
          {checks.map(([service, check]) => (
            <li key={service} className="text-sm">
              {label(service)} : {stateText(service, check.ok)}
              {!check.ok && service !== "llm" && check.detail ? (
                <span className="text-muted-foreground"> — {check.detail}</span>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
      <p role="status" className={`text-sm empty:sr-only ${tone}`}>
        {announcement}
      </p>
    </div>
  );
}
