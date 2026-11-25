import { HealthIndicator } from "@/features/health/components/HealthIndicator";
import { useHealth } from "@/features/health/hooks/useHealth";

/** Connects `useHealth` to the indicator (the feature component stays presentational). */
export function HealthStatus() {
  const { data, isLoading, isError } = useHealth();
  return <HealthIndicator report={data} isLoading={isLoading} isError={isError} />;
}
