import { t } from "@/shared/i18n/t";
import { EmbeddingProgressBar } from "../../components/EmbeddingProgressBar";
import { ServiceChecklist } from "../../components/ServiceChecklist";
import { useEmbeddingProgress } from "../../hooks/useEmbeddingProgress";
import { useServiceHealth } from "../../hooks/useServiceHealth";

/** Étape 1 : l'état de chaque service (relu toutes les 5 s) et la progression de `bge-m3`. */
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
