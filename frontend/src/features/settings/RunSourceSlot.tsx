import { useRunSource } from "@/shared/lib/runSource";
import { RunSourceMenu } from "@/shared/session-ui";
import { useApiKeys } from "./hooks/useApiKeys";

/**
 * Le menu « Qui fait tourner les agents » : dans le panneau (emplacement `topbar`) et, détaillé,
 * en tête de Réglages > Modèles. Les API sans clé enregistrée sont grisées.
 */
export function RunSourceSlot({ detailed = false }: { detailed?: boolean }) {
  const [value, setValue] = useRunSource();
  const keys = useApiKeys();
  const keyed = new Set(
    (keys.data ?? []).filter((entry) => entry.last4 != null).map((entry) => entry.provider),
  );
  return <RunSourceMenu value={value} onChange={setValue} keyed={keyed} detailed={detailed} />;
}
