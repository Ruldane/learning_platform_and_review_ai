import type { SettingsOut } from "../types";
import { planKeys } from "../keyPlan";
import { useApiKeys } from "./useApiKeys";
import { useModels } from "./useModels";

/**
 * The keys and models read for the first run, and what results from them (`planKeys`). Nothing
 * is computed while either read is missing: `entries` and `plan` stay undefined.
 */
export function useKeyPlan(settings: SettingsOut) {
  const keys = useApiKeys();
  const models = useModels();
  const plan = keys.data && models.data ? planKeys(keys.data, models.data, settings) : undefined;
  return { keys, models, plan, entries: plan?.entries };
}
