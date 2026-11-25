import { t } from "@/shared/i18n/t";
import { EmbeddingProgressBar } from "../../components/EmbeddingProgressBar";
import { ServiceChecklist } from "../../components/ServiceChecklist";
import { useEmbeddingProgress } from "../../hooks/useEmbeddingProgress";
import { useServiceHealth } from "../../hooks/useServiceHealth";

/** Step 1: the state of each service (reread every 5 s) and the progress of `bge-m3`. */
export function HealthStep() {
  const health = useServiceHealth();
  const embedding = useEmbeddingProgress();
  return (
    <div className="flex flex-col gap-5">
      <p className="text-muted-foreground">{t("onboarding.health.intro")}</p>
      <ServiceChecklist
        report={health.data}
        isLoading={health.isLoading}
        isError={health.isError}
      />
      <EmbeddingProgressBar progress={embedding.data} isError={embedding.isError} />
    </div>
  );
}
