import { HealthIndicator } from "@/features/health/components/HealthIndicator";
import { useHealth } from "@/features/health/hooks/useHealth";

/** Branche `useHealth` sur le voyant (le composant de la feature reste présentationnel). */
export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();
  return <HealthIndicator report={data} isLoading={isLoading} isError={isError} />;
}
