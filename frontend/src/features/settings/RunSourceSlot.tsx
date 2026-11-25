import { useRunSource } from "@/shared/lib/runSource";
import { RunSourceMenu } from "@/shared/session-ui";
import { useApiKeys } from "./hooks/useApiKeys";

/**
 * The « Qui fait tourner les agents » menu: in the panel (`topbar` slot) and, detailed,
 * at the top of Settings > Models. APIs with no saved key are greyed out.
 */
export function RunSourceSlot({ detailed = false }: { detailed?: boolean }) {
  const [value, setValue] = useRunSource();
  const keys = useApiKeys();
  const keyed = new Set(
    (keys.data ?? []).filter((entry) => entry.last4 != null).map((entry) => entry.provider),
  );
  return <RunSourceMenu value={value} onChange={setValue} keyed={keyed} detailed={detailed} />;
}
