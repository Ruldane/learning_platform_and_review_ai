import type { MessageKey } from "@/shared/i18n/t";
import { t } from "@/shared/i18n/t";

/** Forme du rapport de `GET /health` (types générés ; non importés, la règle de découpage l'interdit). */
interface HealthReportView {
  status: "ok" | "degraded" | "down";
  checks: Record<string, { ok: boolean; detail: string }>;
}

interface ServiceChecklistProps {
  report?: HealthReportView;
  isLoading: boolean;
  /** La dernière lecture a échoué (le prochain tour réessaie tout seul). */
  isError: boolean;
}

const SERVICES = ["db", "llm", "qdrant", "ollama", "searxng"] as const;
type KnownService = (typeof SERVICES)[number];

const isKnown = (service: string): service is KnownService =>
  (SERVICES as readonly string[]).includes(service);

const label = (service: string): string =>
  isKnown(service) ? t(`onboarding.health.services.${service}` as MessageKey) : service;

/** La clé d'un modèle n'est demandée qu'à l'étape 3 : son absence n'est pas une panne ici. */
function stateText(service: string, ok: boolean): string {
  if (ok) return t("onboarding.health.ok");
  return service === "llm" ? t("onboarding.health.keyLater") : t("onboarding.health.down");
}

/**
 * Un état écrit par service (jamais la couleur seule). Les services inconnus du front gardent
 * leur nom brut ; le détail du back (français, sans secret) suit pour un service en panne.
 */
export function ServiceChecklist({ report, isLoading, isError }: ServiceChecklistProps) {
  const checks = Object.entries(report?.checks ?? {});
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
      {isError ? (
        <p role="status" className="text-sm text-destructive">
          {t("onboarding.health.unreachable")}
        </p>
      ) : null}
      {isLoading && checks.length === 0 && !isError ? (
        <p role="status" className="text-sm text-muted-foreground">
          {t("onboarding.health.checking")}
        </p>
      ) : null}
    </div>
  );
}
