import { useEffect, useRef, useState } from "react";
import type { MessageKey } from "@/shared/i18n/t";
import { t } from "@/shared/i18n/t";

/** Forme du rapport de `GET /health` (types générés ; non importés : la règle de découpage). */
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

/** Les services qui répondent de nouveau depuis la lecture d'avant, dits d'un seul texte. */
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
 * Un état écrit par service (jamais la couleur seule). Les services inconnus du front gardent
 * leur nom brut ; le détail du back (français, sans secret) suit pour un service en panne. Une
 * seule zone `status`, toujours dans la page : son texte ne change qu'aux moments utiles (lecture
 * impossible, vérification en cours, service revenu), pas à chaque relecture.
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
