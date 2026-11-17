import type { SettingsOut } from "../types";
import { planKeys } from "../keyPlan";
import { useApiKeys } from "./useApiKeys";
import { useModels } from "./useModels";

/**
 * Les clés et les modèles lus pour le premier lancement, et ce qu'il en résulte (`planKeys`). Rien
 * n'est calculé tant que l'une des deux lectures manque : `entries` et `plan` restent indéfinis.
 */
export function useKeyPlan(settings: SettingsOut) {
  const keys = useApiKeys();
  const models = useModels();
  const plan = keys.data && models.data ? planKeys(keys.data, models.data, settings) : undefined;
  return { keys, models, plan, entries: plan?.entries };
}
